import ct4f_config as config
import ct4f_translator as translator
import ct4f_translator_dialogs as translator_dialogs
import ct4f_ui_dialogs as ui_dialogs
import ct4f_core_functions as fn
import ct4f_security as security
import ct4f_settings as settings
import ct4f_ui_widgets as ui_widgets
#import ct4f_unit_tests as unit_tests
import queue
import threading
from pathlib import Path
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image


ctk.set_appearance_mode("light")
ctk.set_default_color_theme(fn.resource_path("assets/ct4f-theme.json"))

for font_file in ("Almendra-Regular.ttf", "Almendra-Bold.ttf", "EBGaramond-Regular.ttf"):
    ctk.FontManager.load_font(fn.resource_path(f"assets/fonts/{font_file}"))

BANNER_HEIGHT = 90
BANNER_IMAGE_WIDTH_RATIO = 0.95   # share of the banner width covered by the image

SW_IMAGE_HEIGHT_RATIO = 0.43   # share of the frame height covered by the image

MENU_WIDTH_WIDE = 300      # Source Language / Game System (and the full-width controls below them)
MENU_WIDTH_NARROW = 170    # Target Language / Genre
MENU_GAP_WIDTH = 40        # gap between the two dropdowns of a pair
VALUE_LABEL_WIDTH = 90     # the "n chars" label next to the slider

FONT_NAME = ("Almendra", 16, "bold")   # field names and buttons
FONT_VALUE = ("EB Garamond", 17)       # displayed values

BIG_BUTTON_FONT = FONT_NAME
BIG_BUTTON_WIDTH = 220
BIG_BUTTON_HEIGHT = 56
BIG_BUTTON_CORNER_RADIUS = 12
BIG_BUTTON_BORDER_WIDTH = 3
BIG_BUTTON_BORDER_COLOR = config.INK   # same ink brown as the text



class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Initialize Logger
        self.LOGGER = self.log_message

        ui_dialogs.set_logger(self.LOGGER)

        self.title(config.APP_FULL_NAME)
        self.iconbitmap(fn.resource_path("assets/icon.ico"))
        self.calculate_window_dimensions(min_width=800, min_height=800, factor=0.80)

        # =========================================
        # Layout skeleton
        # =========================================
        self.banner_frame = ctk.CTkFrame(self, height=BANNER_HEIGHT, fg_color=config.PARCHMENT, corner_radius=0)
        self.banner_frame.pack(side="top", fill="x")
        self.banner_frame.pack_propagate(False)
        self.banner_source_image = Image.open(fn.resource_path("assets/img/banner.png"))

        self.banner_image = None
        self.banner_image_width = 0

        self.banner_image_label = ctk.CTkLabel(self.banner_frame, text="")
        self.banner_image_label.place(x=0, y=0)

        self.banner_frame.bind("<Configure>", self.on_banner_resized)
        ctk.CTkLabel(self.banner_frame, text="", image=self.banner_image).place(x=0, y=0)

        # Status Bar. Populated on demand by show_status()
        self.status_bar = ctk.CTkFrame(self, height=40)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        self.status_label = ctk.CTkLabel(self.status_bar, text="Ready", anchor="w")
        self.status_label.pack(side="left", padx=20)

        # The "Open Output" belongs to the status bar, but it will only be shown with the final status by show_results()
        self.open_output_button = ctk.CTkButton(
            self.status_bar,
            text="Open Output Folder",
            width=140,
            command=lambda: fn.open_folder(config.OUTPUT_DIR)
        )

        self.body_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.body_frame.pack(side="top", fill="both", expand=True)
        self.body_frame.grid_columnconfigure(0, weight=1)
        self.body_frame.grid_columnconfigure(1, weight=1)
        self.body_frame.grid_rowconfigure(0, weight=1)

        self.configuration_frame = ctk.CTkFrame(self.body_frame)
        self.configuration_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.configuration_frame.grid_columnconfigure(0, weight=0)
        self.configuration_frame.grid_columnconfigure(1, weight=1)

        # Decorative image in the free bottom-left zone. It is place()d (not gridded), so it doesn't
        # affect the layout, and it's created first, so all widgets are drawn on top of it
        self.sw_source_image = Image.open(fn.resource_path("assets/img/sw-image.png"))
        self.sw_image = None
        self.sw_image_size = None

        self.sw_image_label = ctk.CTkLabel(self.configuration_frame, text="")
        self.sw_image_label.place(relx=0, rely=1, anchor="sw")
        self.configuration_frame.bind("<Configure>", self.on_configuration_resized)

        self.monitoring_frame = ctk.CTkFrame(self.body_frame)
        self.monitoring_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))


        # =========================================
        # Settings button
        # =========================================
        self.settings_button = ctk.CTkButton(
            self.banner_frame, text="⚙", width=60, height=60, command=self.open_settings, font=FONT_VALUE
        )
        self.settings_button.pack(side="right", padx=10, pady=5)

        # =========================================
        # Input File picker
        # =========================================
        self.selected_file = None

        ctk.CTkLabel(self.configuration_frame, text="Input File", anchor="w", font=FONT_NAME) \
            .grid(row=0, column=0, sticky="w", padx=(20, 10), pady=(20, 5))

        self.file_button = ctk.CTkButton(
            self.configuration_frame,
            text="Select Input File",
            command=self.select_file
        )
        self.file_button.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=(20, 5))

        self.file_label = ctk.CTkLabel(
            self.configuration_frame,
            text="No file selected",
            anchor="w",
            font=FONT_VALUE
        )
        self.file_label.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=(0, 10))

        # =========================================
        # Output folder picker (optional)
        # =========================================
        self.selected_output_dir = None
        self.output_dir_default_text = "Default: user data folder"

        ctk.CTkLabel(self.configuration_frame, text="Output Folder", anchor="w", font=FONT_NAME) \
            .grid(row=2, column=0, sticky="w", padx=(20, 10), pady=(0, 5))

        self.output_dir_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.output_dir_frame.grid(row=2, column=1, sticky="w", padx=(0, 20), pady=(0, 5))

        self.output_dir_button = ctk.CTkButton(
            self.output_dir_frame,
            text="Select Output Folder",
            command=self.select_output_dir
        )
        self.output_dir_button.pack(side="left", padx=(0, 10))

        self.output_dir_reset_button = ctk.CTkButton(
            self.output_dir_frame,
            text="Reset",
            width=70,
            command=self.reset_output_dir
        )
        self.output_dir_reset_button.pack(side="left")

        self.output_dir_label = ctk.CTkLabel(
            self.configuration_frame,
            text=self.output_dir_default_text,
            anchor="w",
            font=FONT_VALUE
        )
        self.output_dir_label.grid(row=3, column=1, sticky="w", padx=(0, 20), pady=(0, 10))

        # =========================================
        # Input type selector
        # =========================================
        ctk.CTkLabel(self.configuration_frame, text="Input Type", anchor="w", font=FONT_NAME) \
            .grid(row=4, column=0, sticky="w", padx=(20, 10), pady=5)

        self.input_type_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.input_type_frame.grid(row=4, column=1, sticky="w", padx=(0, 20), pady=5)

        self.input_type_var = ctk.StringVar(value=config.INPUT_TYPE_BABELE)
        self.input_type_var.trace_add("write", self.on_input_type_changed)

        self.radio_input_type_babele = ctk.CTkRadioButton(
            self.input_type_frame,
            font=FONT_VALUE,
            text=config.INPUT_TYPE_BABELE,
            variable=self.input_type_var,
            value=config.INPUT_TYPE_BABELE
        )
        self.radio_input_type_babele.pack(side="left", padx=(0, 20))

        self.radio_input_type_localization = ctk.CTkRadioButton(
            self.input_type_frame,
            font=FONT_VALUE,
            text=config.INPUT_TYPE_LOCALIZATION,
            variable=self.input_type_var,
            value=config.INPUT_TYPE_LOCALIZATION
        )
        self.radio_input_type_localization.pack(side="left")

        # =========================================
        # Language selection
        # =========================================
        self.language_options = [
            f"{lang['code']}: {lang['name']}" for lang in config.SUPPORTED_LANGUAGES
        ]
        self.language_by_option = {
            option: lang for option, lang in zip(self.language_options, config.SUPPORTED_LANGUAGES)
        }

        ctk.CTkLabel(self.configuration_frame, text="Language", anchor="w", font=FONT_NAME) \
            .grid(row=5, column=0, sticky="w", padx=(20, 10), pady=5)

        self.language_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.language_frame.grid(row=5, column=1, sticky="w", padx=(0, 20), pady=5)

        self.source_language_var = ctk.StringVar(
            value=f"{config.SOURCE_LANGUAGE['code']}: {config.SOURCE_LANGUAGE['name']}"
        )
        self.source_language_menu = ctk.CTkOptionMenu(
            self.language_frame,
            width=MENU_WIDTH_WIDE,
            dynamic_resizing=False,
            values=self.language_options,
            variable=self.source_language_var
        )
        self.source_language_menu.grid(row=0, column=0)

        ctk.CTkLabel(self.language_frame, text="→", width=MENU_GAP_WIDTH, font=FONT_NAME).grid(row=0, column=1)

        self.target_language_var = ctk.StringVar(
            value=f"{config.TARGET_LANGUAGE['code']}: {config.TARGET_LANGUAGE['name']}"
        )
        self.target_language_menu = ctk.CTkOptionMenu(
            self.language_frame,
            width=MENU_WIDTH_NARROW,
            dynamic_resizing=False,
            values=self.language_options,
            variable=self.target_language_var
        )
        self.target_language_menu.grid(row=0, column=2)

        # =========================================
        # Translation Flavour (Game System / Genre)
        # =========================================
        ctk.CTkLabel(self.configuration_frame, text="Flavour", anchor="w", font=FONT_NAME) \
            .grid(row=6, column=0, sticky="w", padx=(20, 10), pady=5)

        self.flavour_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.flavour_frame.grid(row=6, column=1, sticky="w", padx=(0, 20), pady=5)

        self.game_system_var = ctk.StringVar(value=config.GAME_SYSTEM_CONTEXT)
        self.game_system_menu = ctk.CTkOptionMenu(
            self.flavour_frame,
            width=MENU_WIDTH_WIDE,
            dynamic_resizing=False,
            values=config.SUPPORTED_GAME_SYSTEMS,
            variable=self.game_system_var
        )
        self.game_system_menu.grid(row=0, column=0)

        ctk.CTkLabel(self.flavour_frame, text="", width=MENU_GAP_WIDTH).grid(row=0, column=1)

        self.genre_var = ctk.StringVar(value=config.GENRE_CONTEXT)
        self.genre_menu = ctk.CTkOptionMenu(
            self.flavour_frame,
            width=MENU_WIDTH_NARROW,
            dynamic_resizing=False,
            values=config.SUPPORTED_GENRES,
            variable=self.genre_var
        )
        self.genre_menu.grid(row=0, column=2)

        # =========================================
        # Module name suggestion (editable)
        # =========================================
        ctk.CTkLabel(self.configuration_frame, text="Module Name", anchor="w", font=FONT_NAME) \
            .grid(row=7, column=0, sticky="w", padx=(20, 10), pady=5)

        self.module_name_entry = ctk.CTkEntry(
            self.configuration_frame,
            width=MENU_WIDTH_WIDE,
            font=FONT_VALUE
        )
        self.module_name_entry.grid(row=7, column=1, sticky="w", padx=(0, 20), pady=5)
        self.module_name_entry.insert(0, "(Please pick a file first)")

        # =========================================
        # Max Batch Size
        # =========================================
        ctk.CTkLabel(self.configuration_frame, text="Max Batch Size", anchor="w", font=FONT_NAME) \
            .grid(row=8, column=0, sticky="w", padx=(20, 10), pady=5)

        self.max_batch_size_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.max_batch_size_frame.grid(row=8, column=1, sticky="w", padx=(0, 20), pady=5)

        self.max_batch_size_slider = ctk.CTkSlider(
            self.max_batch_size_frame,
            width=MENU_WIDTH_WIDE - VALUE_LABEL_WIDTH - 10,
            from_=500,
            to=100000,
            number_of_steps=199,
            command=self.on_max_batch_size_changed
        )
        self.max_batch_size_slider.set(config.MAX_BATCH_SIZE)
        self.max_batch_size_slider.pack(side="left")

        self.max_batch_size_label = ctk.CTkLabel(
            self.max_batch_size_frame,
            width=VALUE_LABEL_WIDTH,
            anchor="w",
            text=f"{config.MAX_BATCH_SIZE:,} chars",
            font=FONT_VALUE
        )
        self.max_batch_size_label.pack(side="left", padx=(10, 0))

        # =========================================
        # Mock Mode Switch
        # =========================================
        self.mock_mode_var = ctk.BooleanVar(value=config.MOCK_MODE)
        self.mock_switch = ctk.CTkSwitch(
            self.configuration_frame,
            font=FONT_VALUE,
            text="Simulate only",
            variable=self.mock_mode_var,
            command=self.on_mock_mode_changed,
            progress_color=config.RED,
            fg_color=config.GREY
        )
        self.mock_switch.grid(row=9, column=1, sticky="w", padx=(0, 20), pady=(5, 20))

        # =========================================
        # Prepare / Start / Reset / Cancel Buttons
        # =========================================
        self.start_frame = ctk.CTkFrame(self.monitoring_frame, fg_color="transparent")
        self.start_frame.pack(padx=20, pady=20)

        self.main_button = ctk.CTkButton(
            self.start_frame,
            text="Prepare",
            command=self.prepare,
            width=BIG_BUTTON_WIDTH,
            height=BIG_BUTTON_HEIGHT,
            font=BIG_BUTTON_FONT,
            corner_radius=BIG_BUTTON_CORNER_RADIUS,
            border_width=BIG_BUTTON_BORDER_WIDTH,
            border_color=BIG_BUTTON_BORDER_COLOR
        )
        self.main_button.pack(side="left")

        self.main_button_default_color = self.main_button.cget("fg_color")
        self.main_button_default_hover_color = self.main_button.cget("hover_color")
        self.main_button_default_text_color = self.main_button.cget("text_color")

        # Only visible after a successful preparation (see show_reset_button)
        self.reset_button = ctk.CTkButton(
            self.start_frame,
            text="Reset",
            fg_color=config.INK_LIGHT,
            command=self.reset_preparation,
            width=BIG_BUTTON_WIDTH,
            height=BIG_BUTTON_HEIGHT,
            font=BIG_BUTTON_FONT,
            corner_radius=BIG_BUTTON_CORNER_RADIUS,
            border_width=BIG_BUTTON_BORDER_WIDTH,
            border_color=BIG_BUTTON_BORDER_COLOR
        )

        # =========================================
        # Batch status bars and Stats Info Box
        # (hidden until the batches are known)
        # =========================================
        self.bars_frame = ctk.CTkFrame(self.monitoring_frame, fg_color="transparent")

        # Stats Info Box: a framed "card" with one grid row per stat (name | value), values are set in show_bars
        self.stats_frame = ctk.CTkFrame(
            self.bars_frame,
            fg_color=config.PARCHMENT_LIGHT,
            border_width=2,
            border_color=config.INK_LIGHT,
            corner_radius=8
        )
        self.stats_frame.pack(fill="x", pady=(0, 10))

        self.stats_grid = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.stats_grid.pack(anchor="w", padx=15, pady=10)

        self.chars_name_label = ctk.CTkLabel(self.stats_grid, text="Chars:", anchor="w", font=FONT_NAME)
        self.chars_name_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.chars_value_label = ctk.CTkLabel(self.stats_grid, text="", anchor="w", font=FONT_VALUE)
        self.chars_value_label.grid(row=0, column=1, sticky="w")

        self.batches_name_label = ctk.CTkLabel(self.stats_grid, text="Batches:", anchor="w", font=FONT_NAME)
        self.batches_name_label.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.batches_value_label = ctk.CTkLabel(self.stats_grid, text="", anchor="w", font=FONT_VALUE)
        self.batches_value_label.grid(row=1, column=1, sticky="w")

        # Only shown when there are Review Items (see show_bars)
        self.review_name_label = ctk.CTkLabel(
            self.stats_grid, text="Review Items:", anchor="w",
            text_color=config.MAGENTA, font=FONT_NAME
        )
        self.review_name_label.grid(row=2, column=0, sticky="w", padx=(0, 10))
        self.review_value_label = ctk.CTkLabel(
            self.stats_grid, text="", anchor="w",
            text_color=config.MAGENTA, font=FONT_NAME
        )
        self.review_value_label.grid(row=2, column=1, sticky="w")
        self.review_name_label.grid_remove()
        self.review_value_label.grid_remove()

        self.review_show_button = ctk.CTkButton(
            self.stats_grid,
            text="Show",
            width=60,
            height=24,
            command=self.show_review_items
        )
        self.review_show_button.grid(row=2, column=2, sticky="w", padx=(10, 0))
        self.review_show_button.grid_remove()

        # Terminology Progress Bar
        self.terminology_bar = ui_widgets.BatchStatusBar(
            self.bars_frame,
            "Terminology",
            on_clear=self.confirm_clear_terminology
        )
        self.terminology_bar.pack(fill="x", pady=(0, 10))

        # Terminology Progress Bar
        self.translation_bar = ui_widgets.BatchStatusBar(
            self.bars_frame,
            "Translation",
            on_clear=self.confirm_clear_translation
        )
        self.translation_bar.pack(fill="x")


        # =========================================
        # Log Output Window
        # =========================================
        self.log_popout_button = ctk.CTkButton(
            self.monitoring_frame,
            text="Pop Out Log",
            width=100,
            command=lambda: ui_dialogs.LogViewerDialog(self.monitoring_frame, self.log_window.get("1.0", "end"))
        )
        self.log_popout_button.pack(padx=20, pady=(10, 0), anchor="e")


        # =========================================
        # Log Output Window
        # =========================================
        self.log_window = ctk.CTkTextbox(
            self.monitoring_frame, width=600, height=300,
            fg_color=config.LOG_BACKGROUND_COLOR, text_color=config.LOG_TEXT_COLOR, font=config.LOG_FONT
        )
        for tag, color in config.LOG_TAG_COLORS.items():
            self.log_window.tag_config(tag, foreground=color)
        self.log_window.pack(padx=20, pady=20, fill="both", expand=True)


        # =========================================
        # Enable only the UI elements that are relevant first
        # =========================================
        self.disable_configuration_controls()
        self.file_button.configure(state="normal")
        self.output_dir_button.configure(state="normal")
        self.output_dir_reset_button.configure(state="normal")

        # =========================================
        # Some initialization of dialog-relevant queues
        # =========================================
        self.current_request = None
        self.current_confirm_dialog = None
        self.cancel_event = threading.Event()

        # =========================================
        # Now go for it!
        # =========================================
        self.show_status("Waiting for configuration...")
        self.render_dialog_requests()


    # ===========================================
    # Function: Select File
    # Generated a UI File Picker for selecting the Input File
    # ===========================================
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="Select file to translate",
            filetypes=[("JSON files", "*.json")],
            initialdir=str(self.selected_file.parent) if self.selected_file else None
        )

        if not filename:
            return

        self.set_input_file(Path(filename))


    # ===========================================
    # Function: Set Input File
    # Applies the given file as Input File
    # (shared by the file picker and the settings restore)
    # ===========================================
    def set_input_file(self, file: Path):
        self.selected_file = file

        config.INPUT_FILE = self.selected_file
        config.INPUT_FILE_NAME = self.selected_file.name

        self.file_label.configure(
            text=config.INPUT_FILE_NAME
        )

        self.enable_configuration_controls()

        self.refresh_module_name_suggestion()


    # ===========================================
    # Function: Select Output Dir
    # Generates a UI Folder Picker for the optional Output Folder
    # ===========================================
    def select_output_dir(self):
        dirname = filedialog.askdirectory(
            title="Select output folder",
            initialdir=str(self.selected_output_dir) if self.selected_output_dir else None
        )

        if not dirname:
            return

        self.selected_output_dir = Path(dirname)
        self.output_dir_label.configure(text=str(self.selected_output_dir))


    # ===========================================
    # Function: Reset Output Dir
    # Discards the user-selected Output Folder, so that the default applies again
    # ===========================================
    def reset_output_dir(self):
        self.selected_output_dir = None
        self.output_dir_label.configure(text=self.output_dir_default_text)


    # ===========================================
    # Function: Prepare
    # Takes over the user's selections and runs the preparation (offline part)
    # in a worker thread
    # ===========================================
    def prepare(self):

        if self.source_language_var.get() == self.target_language_var.get():
            ui_dialogs.HintDialog(self, message="Source and Target Language must be different.")
            return

        config.INPUT_TYPE = self.input_type_var.get()
        config.MODULE_NAME = self.module_name_entry.get().strip()
        config.BASE_OUTPUT_DIR = self.selected_output_dir  # None => fall back to USER_DATA_DIR
        config.SOURCE_LANGUAGE = self.language_by_option[self.source_language_var.get()]
        config.TARGET_LANGUAGE = self.language_by_option[self.target_language_var.get()]
        config.GAME_SYSTEM_CONTEXT = self.game_system_var.get()
        config.GENRE_CONTEXT = self.genre_var.get()
        config.MAX_BATCH_SIZE = int(round(self.max_batch_size_slider.get()))

        fn.adapt_file_paths()
        self.persist_settings()

        self.disable_configuration_controls()
        self.show_status("Preparing...")

        threading.Thread(
            target=translator.prepare,
            kwargs={
                "logger": self.log_message,
                "on_ended": self.preparation_ended
            },
            daemon=True
        ).start()


    # ===========================================
    # Function: Enter Prepared State
    # The selections are now final: the "Prepare" button turns into "Start",
    # and "Reset" allows to go back
    # ===========================================
    def enter_prepared_state(self, result):
        self.prepared_result = result
        self.set_main_button_role("Start ▶▶", self.run_translation, color=config.GREEN)
        self.show_reset_button()
        self.show_bars(result["analysis"])
        self.update_clear_buttons(result["analysis"])
        self.show_status("Ready to start.")


    # ===========================================
    # Function: Reset Preparation
    # Goes back from the prepared state to the initial "choose" state
    # ===========================================
    def reset_preparation(self):
        self.prepared_result = None
        self.hide_reset_button()
        self.set_main_button_role("Prepare", self.prepare)
        self.enable_configuration_controls()
        self.hide_bars()
        self.show_status("Waiting for configuration...")


    # ===========================================
    # Function: Show Bars
    # Renders the batch status bars from the analysis delivered by the preparation
    # ===========================================
    def show_bars(self, analysis):
        batches = analysis["batches"]

        # Stats Info Box
        self.chars_value_label.configure(text=f"{sum(batch['char_count'] for batch in batches):,}")
        self.batches_value_label.configure(text=str(len(batches)))

        review_item_count = analysis["review_item_count"]
        if review_item_count > 0:
            self.review_value_label.configure(text=str(review_item_count))
            self.review_name_label.grid()
            self.review_value_label.grid()
            self.review_show_button.grid()
        else:
            self.review_name_label.grid_remove()
            self.review_value_label.grid_remove()
            self.review_show_button.grid_remove()

        self.terminology_bar.set_batches([
            {
                "batch_id": batch["id"],
                "status": batch[config.TERMINOLOGY_STATUS],
                "char_count": batch["char_count"]
            }
            for batch in batches
        ])

        self.translation_bar.set_batches([
            {
                "batch_id": batch["id"],
                "status": batch[config.TRANSLATION_STATUS],
                "char_count": batch["char_count"]
            }
            for batch in batches
        ])

        self.bars_frame.pack(before=self.log_popout_button, padx=20, pady=5, fill="x")


    # ===========================================
    # Function: Hide Bars
    # ===========================================
    def hide_bars(self):
        self.bars_frame.pack_forget()


    # ===========================================
    # Function: Batches Changed
    # Listener for Batch status changes (see fn.set_batch_listener).
    # Invoked by the worker thread, so it hands over to the UI thread
    # ===========================================
    def batches_changed(self, data):
        self.after(
            0,
            lambda: self.show_bars(data)
        )


    # ===========================================
    # Function: Status Changed
    # Listener for status messages (see fn.set_status_listener).
    # Invoked by the worker thread, so it hands over to the UI thread
    # ===========================================
    def status_changed(self, message):
        self.after(
            0,
            lambda: self.show_status(message)
        )

    # ===========================================
    # Function: Set Clear Buttons Enabled
    # Locks/unlocks both Clear buttons at once
    # ===========================================
    def set_clear_buttons_enabled(self, enabled):
        self.terminology_bar.set_clear_enabled(enabled)
        self.translation_bar.set_clear_enabled(enabled)


    # ===========================================
    # Function: Update Clear Buttons
    # Enables each Clear button only if there is anything to discard
    # ===========================================
    def update_clear_buttons(self, analysis):
        batches = analysis["batches"]

        self.terminology_bar.set_clear_enabled(fn.is_terminology_clearable(batches))
        self.translation_bar.set_clear_enabled(fn.is_translation_clearable(batches))


    # ===========================================
    # Function: Confirm Clear
    # Asks for confirmation, then runs the given clear function and refreshes the bars
    # ===========================================
    def confirm_clear(self, question, clear_function):

        def on_yes():
            clear_function()
            analysis = fn.analyze_progress_info()
            self.show_bars(analysis)
            self.update_clear_buttons(analysis)

        ui_dialogs.confirm_yes_no(
            question=question,
            on_yes=on_yes,
            on_no=None
        )


    # ===========================================
    # Function: Confirm Clear Terminology
    # ===========================================
    def confirm_clear_terminology(self):
        self.confirm_clear(
            question=(
                "Clear Terminology?\n\n"
                "This discards the terminology already built for this input file. "
                "It will be rebuilt from scratch with new remote AI calls.\n"
                "Existing translations stay as they are, based on the old terminology. "
                "To apply the new terminology to them as well, clear the translations too.\n\n"
                "Do you want to proceed?"
            ),
            clear_function=fn.clear_terminology
        )


    # ===========================================
    # Function: Confirm Clear Translation
    # ===========================================
    def confirm_clear_translation(self):
        self.confirm_clear(
            question=(
                "Clear Translations?\n\n"
                "This discards all translations already made for this input file. "
                "Everything will be translated from scratch with new remote AI calls.\n\n"
                "Do you want to proceed?"
            ),
            clear_function=fn.clear_translation
        )


    # ===========================================
    # Function: Reset UI
    # Restores the initial state before pressing
    # the "Prepare" Button
    # (without dropping existing input)
    # ===========================================
    def reset_ui(self):
        self.reset_preparation()


    # ===========================================
    # Function: Run Translation
    # Starts the main worker thread (translation) asynchronously
    # ===========================================
    def run_translation(self) -> bool:

        # Pre-flight check: Do we have an API key on board?
        if not config.MOCK_MODE and not security.has_api_key():
            self.open_settings(callback=self.run_translation)
            return False

        self.cancel_event.clear()
        self.hide_reset_button()
        self.set_clear_buttons_enabled(False)

        if config.INPUT_FILE is None:
            self.LOGGER("Please select an input file first.", config.TAG_ERROR)
            return False

        self.disable_configuration_controls()

        # The main button turns into the Cancel button while running
        self.set_main_button_role("Cancel", self.cancel, color=config.YELLOW, text_color=config.INK)
        self.show_status("Running...")

        threading.Thread(
            target=translator.run,
            kwargs={
                "logger": self.log_message,
                "on_ended": self.run_ended,
                "cancel_event": self.cancel_event
            },
            daemon=True
        ).start()

        return True


        # ===========================================
    # Function: Preparation Ended
    # Callback invoked by the worker thread, however the preparing phase ended.
    # Hands over to the UI thread
    # ===========================================
    def preparation_ended(self, outcome):
        self.after(
            0,
            lambda: self.handle_preparation_outcome(outcome)
        )


    # ===========================================
    # Function: Handle Preparation Outcome
    # ===========================================
    def handle_preparation_outcome(self, outcome):

        if outcome["outcome"] == config.OUTCOME_SUCCESS:
            self.enter_prepared_state(outcome["result"])
            return

        # Nothing has been prepared, so back to the start
        self.show_outcome_message(outcome)
        self.reset_ui()
        self.show_outcome_status(outcome)


    # ===========================================
    # Function: Run Ended
    # Callback invoked by the worker thread, however the running phase ended.
    # Hands over to the UI thread
    # ===========================================
    def run_ended(self, outcome):
        self.after(
            0,
            lambda: self.handle_run_outcome(outcome)
        )


    # ===========================================
    # Function: Handle Run Outcome
    # ===========================================
    def handle_run_outcome(self, outcome):
        self.show_outcome_message(outcome)

        # The progress is persisted, whatever happened, so continue from it
        self.return_to_prepared_state()

        if outcome["outcome"] == config.OUTCOME_SUCCESS:
            self.show_results() # needs to be called after return_to_prepared_state, so that results can't get overwritten by the "Ready to start." status message
            fn.play_sound(fn.resource_path("assets/completed.wav"))
        else:
            self.show_outcome_status(outcome)


    # ===========================================
    # Function: Return To Prepared State
    # After a run, the progress is persisted, so the UI continues from a fresh analysis of it
    # ===========================================
    def return_to_prepared_state(self):
        self.enter_prepared_state({"analysis": fn.analyze_progress_info()})


    # ===========================================
    # Function: Process Dialog Requests
    # Processes dialog requests from the translation engine and dynamically
    # displays the corresponding UI elements in the main application window.
    # ===========================================
    def render_dialog_requests(self):

        try:
            request = translator_dialogs.get_request()

        except queue.Empty:
            pass

        else:
            if request["type"] == config.PROMPT_TYPE_YESNO:
                self.show_confirm_dialog(request)

            else:
                self.LOGGER("UNKNOWN REQUEST", config.TAG_ERROR)
                print(f"{config.CONSOLE_RED}UNKNOWN REQUEST{config.CONSOLE_RESET}")

        self.after(50, self.render_dialog_requests)


    # ===========================================
    # Function: Show Confirm Dialog
    # Opens a modal Yes/No dialog for the given request and routes the answer back,
    # either to the worker thread (response_queue) or to a UI-thread callback (on_yes/on_no)
    # ===========================================
    def show_confirm_dialog(self, request):

        self.current_request = request

        def answer(is_yes):
            self.current_request = None
            self.current_confirm_dialog = None

            if "response_queue" in request:
                request["response_queue"].put(config.YES if is_yes else config.NO)
            else:
                callback = request["on_yes"] if is_yes else request["on_no"]
                if callback:
                    callback()

        self.current_confirm_dialog = ui_dialogs.ConfirmDialog(
            self,
            question=request["question"],
            on_yes=lambda: answer(True),
            on_no=lambda: answer(False),
            get_log_text=lambda: self.log_window.get("1.0", "end")
        )


    # ===========================================
    # Function: Show Review Items
    # Opens the pop-out view with the Review Items collected so far
    # ===========================================
    def show_review_items(self):
        review_items = fn.load_json_input(config.PROGRESS_REVIEW_ITEMS_FILE)
        ui_dialogs.ReviewItemsDialog(self, review_items)


    # ===========================================
    # Function: On Input Type Changed
    # Gets alerted whenever a new INPUT_TYPE has selected
    # Ensures that the Module Name Suggestion gets reevaluated
    # ===========================================
    def on_input_type_changed(self, *args):
        self.refresh_module_name_suggestion()


    # ===========================================
    # Function: On Max Batch Size Changed
    # Updates the live readout while the slider is being dragged
    # ===========================================
    def on_max_batch_size_changed(self, value):
        self.max_batch_size_label.configure(text=f"{int(round(value)):,} chars")


    # ===========================================
    # Function: On Mock Mode Changed
    # Gets alerted whenever a the Mock Mode Switch is toggled
    # ===========================================
    def on_mock_mode_changed(self):
        config.MOCK_MODE = bool(self.mock_mode_var.get())
        # self.LOGGER(f"MOCK_MODE = {config.MOCK_MODE}")


    # ===========================================
    # Function: On Banner Resized
    # Rescales the banner image to its share of the banner width
    # ===========================================
    def on_banner_resized(self, event):
        width = int(event.width * BANNER_IMAGE_WIDTH_RATIO)

        if width == self.banner_image_width:
            return

        self.banner_image_width = width
        self.banner_image = ctk.CTkImage(
            light_image=self.banner_source_image,
            size=(width, BANNER_HEIGHT)
        )
        self.banner_image_label.configure(image=self.banner_image)


    # ===========================================
    # Function: On Configuration Resized
    # Rescales the bottom-left image to its share of the frame height (keeping its aspect ratio)
    # ===========================================
    def on_configuration_resized(self, event):
        height = int(event.height * SW_IMAGE_HEIGHT_RATIO)
        width = int(height * self.sw_source_image.width / self.sw_source_image.height)

        if (width, height) == self.sw_image_size:
            return

        self.sw_image_size = (width, height)
        self.sw_image = ctk.CTkImage(light_image=self.sw_source_image, size=self.sw_image_size)
        self.sw_image_label.configure(image=self.sw_image)

    # ===========================================
    # Function: Refresh Module Name Suggestion
    #
    # ===========================================
    def refresh_module_name_suggestion(self):

        if self.selected_file is None:
            return

        suggested_module_name = ui_dialogs.suggest_module_name(
            self.selected_file,
            self.input_type_var.get()
        )

        self.module_name_entry.delete(0, "end")
        self.module_name_entry.insert(0, suggested_module_name)


    # ===========================================
    # Function: Disable Configuration Controls
    #
    # ===========================================
    def disable_configuration_controls(self):

        self.file_button.configure(state="disabled")
        self.output_dir_button.configure(state="disabled")
        self.output_dir_reset_button.configure(state="disabled")
        self.radio_input_type_babele.configure(state="disabled")
        self.radio_input_type_localization.configure(state="disabled")
        self.module_name_entry.configure(state="disabled")
        self.main_button.configure(state="disabled")
        self.mock_switch.configure(state="disabled")
        self.source_language_menu.configure(state="disabled")
        self.target_language_menu.configure(state="disabled")
        self.game_system_menu.configure(state="disabled")
        self.genre_menu.configure(state="disabled")
        self.max_batch_size_slider.configure(state="disabled")


    # ===========================================
    # Function: Enable Configuration Controls
    #
    # ===========================================
    def enable_configuration_controls(self):

        self.file_button.configure(state="normal")
        self.output_dir_button.configure(state="normal")
        self.output_dir_reset_button.configure(state="normal")
        self.radio_input_type_babele.configure(state="normal")
        self.radio_input_type_localization.configure(state="normal")
        self.module_name_entry.configure(state="normal")
        self.main_button.configure(state="normal")
        self.mock_switch.configure(state="normal")
        self.source_language_menu.configure(state="normal")
        self.target_language_menu.configure(state="normal")
        self.game_system_menu.configure(state="normal")
        self.genre_menu.configure(state="normal")
        self.max_batch_size_slider.configure(state="normal")


    # ===========================================
    # Function: Cancel
    # Used by the main button while running.
    # Effective at the next Batch boundary, so a running API call has to be waited out
    # ===========================================
    def cancel(self):
        self.cancel_event.set()
        self.set_main_button_role("Please wait for batch to complete ...", self.cancel, color=config.RED, state="disabled")

        # A pending confirm dialog has to be released as well, because the worker thread
        # blocks while waiting for the answer
        if self.current_confirm_dialog is not None:
            self.current_confirm_dialog.destroy()
            self.current_confirm_dialog = None

        if self.current_request is not None and "response_queue" in self.current_request:
            self.current_request["response_queue"].put(config.CANCEL)
            self.current_request = None


    # ===========================================
    # Function: Set Main Button Role
    # Sets text, command, state and colors of the main button in one go
    # (color/text_color None => back to the default colors)
    # ===========================================
    def set_main_button_role(self, text, command, color=None, text_color=None, state="normal"):
        self.main_button.configure(
            text=text,
            command=command,
            state=state,
            fg_color=color or self.main_button_default_color,
            hover_color=color or self.main_button_default_hover_color,
            text_color=text_color or self.main_button_default_text_color
        )


    # ===========================================
    # Function: Show Reset Button
    # ===========================================
    def show_reset_button(self):
        self.reset_button.pack(side="left", padx=(10, 0))


    # ===========================================
    # Function: Hide Reset Button
    # ===========================================
    def hide_reset_button(self):
        self.reset_button.pack_forget()


    # ===========================================
    # Function: Show Outcome Message
    # Tells the user what happened, depending on how a phase (preparing/running) ended
    # ===========================================
    def show_outcome_message(self, outcome):

        kind = outcome["outcome"]

        if kind == config.OUTCOME_CANCELLED:
            self.LOGGER("Cancelled by user.", config.TAG_WARNING)

        elif kind == config.OUTCOME_DECLINED:
            self.LOGGER("Aborted by user.", config.TAG_WARNING)

        elif kind == config.OUTCOME_EXPECTED_ERROR:
            self.LOGGER(outcome["message"], config.TAG_ERROR)
            ui_dialogs.HintDialog(self, message=outcome["message"])

        elif kind == config.OUTCOME_UNEXPECTED_ERROR:
            msg = f"An unexpected error occurred:\n{outcome['message']}"
            self.LOGGER(msg, config.TAG_ERROR)
            print(outcome["details"])  # full traceback to the console
            ui_dialogs.ErrorDialog(self, message=msg)


    # ===========================================
    # Function: Show Outcome Status
    # One-line status for a phase that did not end successfully
    # ===========================================
    def show_outcome_status(self, outcome):

        kind = outcome["outcome"]

        if kind == config.OUTCOME_CANCELLED:
            self.show_status("Cancelled by user")

        elif kind == config.OUTCOME_DECLINED:
            self.show_status("Aborted by user")

        elif kind == config.OUTCOME_EXPECTED_ERROR:
            self.show_status(f"Error - see log for details: {outcome['message'].splitlines()[0]}")

        elif kind == config.OUTCOME_UNEXPECTED_ERROR:
            self.show_status("Unexpected error - see log for details")


    # ===========================================
    # Function: Show Status
    # Shows a message in the status bar (and hides the results button, which only belongs to results)
    # ===========================================
    def show_status(self, message):
        self.status_label.configure(text=message)
        self.open_output_button.pack_forget() # This is the default, to make sure that the button never stays visible longer than needed


    # ===========================================
    # Function: Show Results
    # Announces the output of a successful run in the status bar
    # ===========================================
    def show_results(self):
        self.show_status(f"Translated file: {config.OUTPUT_FILE}")
        self.open_output_button.pack(side="right", padx=20)


    # ===========================================
    # Function: Log Message
    # Writes the message passed to the configured logger
    # ===========================================
    def log_message(self, message, tag=""):
        self.log_window.insert("end", message + "\n", tag)
        self.log_window.see("end")


    # ===========================================
    # Function: Calculate window size and position
    #
    # ===========================================
    def calculate_window_dimensions(self, min_width=800, min_height=600, factor=0.8):

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width = int(max(screen_width * factor, min_width))
        height = int(max(screen_height * factor, min_height))

        x = int((screen_width - width) // 2)
        y = int((screen_height - height) // 2)

        geometry = f"{width}x{height}+{x}+{y}"
        self.minsize(min_width, min_height)
        self.geometry(geometry)


    # ===========================================
    # Function: Open Settings
    #
    # ===========================================
    def open_settings(self, callback=None):
        ui_dialogs.SettingsDialog(self, on_save_callback=callback)


    # ===========================================
    # Function: Persist Settings
    # Saves the current selections to the settings file (called when a translation starts)
    # ===========================================
    def persist_settings(self):
        settings.save_settings({
            "base_output_dir": str(config.BASE_OUTPUT_DIR) if config.BASE_OUTPUT_DIR else None,
            "input_file": str(config.INPUT_FILE),
            "input_type": config.INPUT_TYPE,
            "module_name": config.MODULE_NAME,
            "source_language_code": config.SOURCE_LANGUAGE["code"],
            "target_language_code": config.TARGET_LANGUAGE["code"],
            "game_system_context": config.GAME_SYSTEM_CONTEXT,
            "genre_context": config.GENRE_CONTEXT,
            "max_batch_size": config.MAX_BATCH_SIZE
        })


    # ===========================================
    # Function: Restore Settings
    # Restores the persisted selections into the UI (called once at app start)
    # ===========================================
    def restore_settings(self):

        try:
            saved = settings.load_settings()

        except (OSError, ValueError):
            msg = \
                 "Couldn't restore previous settings - falling back to defaults.\n\n" \
                f"Please check your local settings file (something seems to be corrupt with it):\n" \
                f"{config.SETTINGS_FILE}."
            self.LOGGER(msg, config.TAG_ERROR)
            if self.LOGGER != print:
                print(msg)
            ui_dialogs.ErrorDialog(self, message=msg)

            return

        # Output folder: independent of the input file
        output_dir = saved.get("base_output_dir")
        if output_dir and Path(output_dir).is_dir():
            self.selected_output_dir = Path(output_dir)
            self.output_dir_label.configure(text=str(self.selected_output_dir))

        # Input file, input type and module name are restored as a unit,
        # so they are dropped together if any part is no longer valid
        input_file = saved.get("input_file")
        input_type = saved.get("input_type")
        module_name = saved.get("module_name")

        # Language pair and batch size: also independent of the input file
        def find_language_option(code):
            for option, lang in self.language_by_option.items():
                if lang["code"] == code:
                    return option
            return None

        source_option = find_language_option(saved.get("source_language_code"))
        if source_option:
            self.source_language_var.set(source_option)

        target_option = find_language_option(saved.get("target_language_code"))
        if target_option:
            self.target_language_var.set(target_option)

        game_system_context = saved.get("game_system_context")
        if game_system_context in config.SUPPORTED_GAME_SYSTEMS:
            self.game_system_var.set(game_system_context)

        genre_context = saved.get("genre_context")
        if genre_context in config.SUPPORTED_GENRES:
            self.genre_var.set(genre_context)

        max_batch_size = saved.get("max_batch_size")
        if isinstance(max_batch_size, int):
            self.max_batch_size_slider.set(max_batch_size)
            self.on_max_batch_size_changed(max_batch_size)

        if not (input_file and Path(input_file).is_file()):
            return

        if input_type not in (config.INPUT_TYPE_BABELE, config.INPUT_TYPE_LOCALIZATION):
            return

        self.set_input_file(Path(input_file))

        # Changing the input type re-triggers the module name suggestion,
        # so the stored module name must be applied last
        self.input_type_var.set(input_type)

        if module_name:
            self.module_name_entry.delete(0, "end")
            self.module_name_entry.insert(0, module_name)


# Initialize the app
app = App()

fn.set_logger(app.LOGGER)

fn.set_batch_listener(app.batches_changed)
fn.set_status_listener(app.status_changed)

fn.init_system_dirs()
app.restore_settings()

# Finally, run it!
app.mainloop()

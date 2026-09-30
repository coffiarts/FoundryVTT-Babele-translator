import cfbt_config as config
import cfbt_translator as translator
import cfbt_translator_dialogs as translator_dialogs
import cfbt_ui_dialogs as ui_dialogs
import cfbt_core_functions as fn
import cfbt_i18n as i18n
import cfbt_security as security
import cfbt_settings as settings
import cfbt_ui_widgets as ui_widgets
#import cfbt_unit_tests as unit_tests
import queue
import threading
from pathlib import Path
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image


# The UI language and font style must be known before the theme is loaded and the window is built.
# Both are persisted in the settings file, whose location is only known after the system dirs
# have been initialized
fn.init_system_dirs()

config.UI_LANGUAGE = settings.load_ui_language()
i18n.load(fn.resource_path("lang"), config.UI_LANGUAGE)

config.UI_THEME = settings.load_ui_theme()

available_themes = fn.available_themes()
theme_extras = available_themes[config.UI_THEME]["extras"]

for category, values in theme_extras.items():
    if not isinstance(values, dict):
        continue  # e.g. "font_files": a list, handled separately below, not merged into config.theme_extras
    target = config.theme_extras.setdefault(category, {})
    for key, value in values.items():
        # One level of merging, so a theme can override e.g. just "fonts.Heading" without
        # losing the other font roles, or "fonts.Heading.size" without losing its family/weight
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            target[key].update(value)
        else:
            target[key] = value

def _font_tuple(font_def):
    return (font_def["family"], font_def["size"], font_def["weight"])

config.FONT_HEADING = _font_tuple(config.theme_extras["fonts"]["Heading"])
config.FONT_TEXT = _font_tuple(config.theme_extras["fonts"]["Text"])
config.FONT_TOOLTIP = _font_tuple(config.theme_extras["fonts"]["Tooltip"])

ctk.set_appearance_mode("light")
ctk.set_default_color_theme(fn.resource_path(available_themes[config.UI_THEME]["file"]))

# Every theme's fonts are loaded upfront, so any theme can be selected without a restart
all_font_files = sorted({
    font_file
    for theme in available_themes.values()
    for font_file in theme["extras"].get("font_files", [])
})
for font_file in all_font_files:
    ctk.FontManager.load_font(fn.resource_path(f"{config.FONTS_DIR}/{font_file}"))

BANNER_HEIGHT = 90
BANNER_IMAGE_WIDTH_RATIO = 0.9   # share of the banner width covered by the image

DECO_IMAGE_HEIGHT_RATIO = 0.43   # share of the frame height covered by the image

MENU_WIDTH_WIDE = 300      # Source Language / Game System (and the full-width controls below them)
MENU_WIDTH_NARROW = 170    # Target Language / Genre
MENU_GAP_WIDTH = 40        # gap between the two dropdowns of a pair
VALUE_LABEL_WIDTH = 90     # the "n chars" label next to the slider

BIG_BUTTON_FONT = config.FONT_HEADING
BIG_BUTTON_WIDTH = 220
BIG_BUTTON_HEIGHT = 56
BIG_BUTTON_CORNER_RADIUS = 12
BIG_BUTTON_BORDER_WIDTH = 3

# Hover info of the main button, depending on its current role (see set_main_button_role)
TOOLTIP_PREPARE = "tooltip.prepare"
TOOLTIP_START = "tooltip.start"
TOOLTIP_CANCEL = "tooltip.cancel"
TOOLTIP_WAITING = "tooltip.waiting"


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Initialize Logger
        self.LOGGER = self.log_message

        ui_dialogs.set_logger(self.LOGGER)

        self.title(config.APP_FULL_NAME)
        self.iconbitmap(fn.resource_path(f"{config.ASSETS_DIR}/icon.ico"))
        self.calculate_window_dimensions(min_width=800, min_height=800, factor=0.80)

        # =========================================
        # Layout skeleton
        # =========================================
        self.banner_frame = ctk.CTkFrame(self, height=BANNER_HEIGHT, corner_radius=0)
        self.banner_frame.pack(side="top", fill="x")
        self.banner_frame.pack_propagate(False)

        self.banner_source_image = Image.open(fn.resource_path(f"{config.IMG_DIR}/{config.theme_extras['images']['banner']}"))
        self.banner_image = None
        self.banner_image_width = 0

        self.banner_image_label = ctk.CTkLabel(self.banner_frame, text="")
        self.banner_image_label.place(x=0, y=0)

        self.banner_frame.bind("<Configure>", self.on_banner_resized)

        # Status Bar. Populated on demand by show_status()
        self.status_bar = ctk.CTkFrame(self, height=40)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        self.status_label = ctk.CTkLabel(self.status_bar, text="", anchor="w")  # set right at startup by show_status()
        self.status_label.pack(side="left", padx=20)

        # The "Open Folder" belongs to the status bar, but it will only be shown when there's a result file to show (terminology or translation)
        self.open_folder_button = ctk.CTkButton(
            self.status_bar,
            text=i18n.t("button.open_output_folder"),
            width=200
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
        self.deco_source_image = Image.open(fn.resource_path(f"{config.IMG_DIR}/{config.theme_extras['images']['deco_image']}"))
        self.deco_image = None
        self.deco_image_size = None

        self.deco_image_label = ctk.CTkLabel(self.configuration_frame, text="")
        self.deco_image_label.place(relx=0, rely=1, anchor="sw")
        self.configuration_frame.bind("<Configure>", self.on_configuration_resized)

        self.monitoring_frame = ctk.CTkFrame(self.body_frame)
        self.monitoring_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))


        # =========================================
        # Settings button
        # =========================================
        self.settings_button = ctk.CTkButton(
            self.banner_frame, text="⚙", width=60, height=60, command=self.open_settings, font=config.FONT_TEXT
        )
        self.settings_button.pack(side="right", padx=10, pady=5)

        # =========================================
        # Help button
        # =========================================
        self.help_button = ctk.CTkButton(
            self.banner_frame, text="?", width=60, height=60, command=self.open_help, font=config.FONT_TEXT
        )
        self.help_button.pack(side="right", padx=10, pady=5)

        # =========================================
        # Input File picker
        # =========================================
        self.selected_file = None

        ctk.CTkLabel(self.configuration_frame, text=i18n.t("label.input_file"), anchor="w", font=config.FONT_HEADING) \
            .grid(row=0, column=0, sticky="w", padx=(20, 10), pady=(20, 5))

        self.file_button = ctk.CTkButton(
            self.configuration_frame,
            text=i18n.t("button.select_input_file"),
            command=self.select_file
        )
        self.file_button.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=(20, 5))

        self.file_label = ctk.CTkLabel(
            self.configuration_frame,
            text=i18n.t("label.no_file_selected"),
            anchor="w",
            font=config.FONT_TEXT
        )
        self.file_label.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=(0, 10))

        # =========================================
        # Output folder picker (optional)
        # =========================================
        self.selected_output_dir = None
        self.output_dir_default_text = i18n.t("label.default_output_folder")

        ctk.CTkLabel(self.configuration_frame, text=i18n.t("label.output_folder"), anchor="w", font=config.FONT_HEADING) \
            .grid(row=2, column=0, sticky="w", padx=(20, 10), pady=(0, 5))

        self.output_dir_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.output_dir_frame.grid(row=2, column=1, sticky="w", padx=(0, 20), pady=(0, 5))

        self.output_dir_button = ctk.CTkButton(
            self.output_dir_frame,
            text=i18n.t("button.select_output_folder"),
            command=self.select_output_dir
        )
        self.output_dir_button.pack(side="left", padx=(0, 10))

        self.output_dir_reset_button = ctk.CTkButton(
            self.output_dir_frame,
            text=i18n.t("button.reset_output_folder"),
            width=70,
            command=self.reset_output_dir
        )
        self.output_dir_reset_button.pack(side="left")

        self.output_dir_label = ctk.CTkLabel(
            self.configuration_frame,
            text=self.output_dir_default_text,
            anchor="w",
            font=config.FONT_TEXT
        )
        self.output_dir_label.grid(row=3, column=1, sticky="w", padx=(0, 20), pady=(0, 10))

        # =========================================
        # Input type selector
        # =========================================
        ctk.CTkLabel(self.configuration_frame, text=i18n.t("label.input_type"), anchor="w", font=config.FONT_HEADING) \
            .grid(row=4, column=0, sticky="w", padx=(20, 10), pady=5)

        self.input_type_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.input_type_frame.grid(row=4, column=1, sticky="w", padx=(0, 20), pady=5)

        self.input_type_var = ctk.StringVar(value=config.INPUT_TYPE_BABELE)
        self.input_type_var.trace_add("write", self.on_input_type_changed)

        self.radio_input_type_babele = ctk.CTkRadioButton(
            self.input_type_frame,
            font=config.FONT_TEXT,
            text=i18n.t("label.input_type_babele"),
            variable=self.input_type_var,
            value=config.INPUT_TYPE_BABELE
        )
        self.radio_input_type_babele.pack(side="left", padx=(0, 20))

        self.radio_input_type_localization = ctk.CTkRadioButton(
            self.input_type_frame,
            font=config.FONT_TEXT,
            text=i18n.t("label.input_type_localization"),
            variable=self.input_type_var,
            value=config.INPUT_TYPE_LOCALIZATION
        )
        self.radio_input_type_localization.pack(side="left")

        # =========================================
        # Module name suggestion (editable)
        # =========================================
        ctk.CTkLabel(self.configuration_frame, text=i18n.t("label.module_name"), anchor="w", font=config.FONT_HEADING) \
            .grid(row=5, column=0, sticky="w", padx=(20, 10), pady=5)

        self.module_name_entry = ctk.CTkEntry(
            self.configuration_frame,
            width=MENU_WIDTH_WIDE,
            font=config.FONT_TEXT
        )
        self.module_name_entry.grid(row=5, column=1, sticky="w", padx=(0, 20), pady=5)
        self.module_name_entry.insert(0, i18n.t("label.pick_file_first"))

        # =========================================
        # Language selection
        # =========================================
        # The display name is localized (language file key "language.<code>"), the English name is the fallback
        self.language_options = [
            f"{lang['code']}: {i18n.t_or('language.' + lang['code'], lang['name'])}" for lang in config.SUPPORTED_LANGUAGES
        ]
        self.language_by_option = {
            option: lang for option, lang in zip(self.language_options, config.SUPPORTED_LANGUAGES)
        }
        language_option_by_code = {lang["code"]: option for option, lang in self.language_by_option.items()}

        ctk.CTkLabel(self.configuration_frame, text=i18n.t("label.language"), anchor="w", font=config.FONT_HEADING) \
            .grid(row=6, column=0, sticky="w", padx=(20, 10), pady=5)

        self.language_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.language_frame.grid(row=6, column=1, sticky="w", padx=(0, 20), pady=5)

        self.source_language_var = ctk.StringVar(
            value=language_option_by_code[config.SOURCE_LANGUAGE["code"]]
        )
        self.source_language_menu = ctk.CTkOptionMenu(
            self.language_frame,
            width=MENU_WIDTH_WIDE,
            dynamic_resizing=False,
            values=self.language_options,
            variable=self.source_language_var
        )
        self.source_language_menu.grid(row=0, column=0)

        ctk.CTkLabel(self.language_frame, text="→", width=MENU_GAP_WIDTH, font=config.FONT_HEADING).grid(row=0, column=1)

        self.target_language_var = ctk.StringVar(
            value=language_option_by_code[config.TARGET_LANGUAGE["code"]]
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
        ctk.CTkLabel(self.configuration_frame, text=i18n.t("label.flavour"), anchor="w", font=config.FONT_HEADING) \
            .grid(row=7, column=0, sticky="w", padx=(20, 10), pady=5)

        self.flavour_frame = ctk.CTkFrame(self.configuration_frame, fg_color="transparent")
        self.flavour_frame.grid(row=7, column=1, sticky="w", padx=(0, 20), pady=5)

        # The dropdowns show localized texts, whereas the (English) values are used everywhere else
        self.game_system_by_option = {
            i18n.t_or(f"game_system.{key}", name): name for key, name in config.GAME_SYSTEMS.items()
        }
        self.game_system_option_by_value = {name: option for option, name in self.game_system_by_option.items()}

        self.game_system_var = ctk.StringVar(value=self.game_system_option_by_value[config.GAME_SYSTEM_CONTEXT])
        self.game_system_menu = ctk.CTkOptionMenu(
            self.flavour_frame,
            width=MENU_WIDTH_WIDE,
            dynamic_resizing=False,
            values=list(self.game_system_by_option),
            variable=self.game_system_var
        )
        self.game_system_menu.grid(row=0, column=0)

        ctk.CTkLabel(self.flavour_frame, text="", width=MENU_GAP_WIDTH).grid(row=0, column=1)

        self.genre_by_option = {
            i18n.t_or(f"genre.{key}", name): name for key, name in config.GENRES.items()
        }
        self.genre_option_by_value = {name: option for option, name in self.genre_by_option.items()}

        self.genre_var = ctk.StringVar(value=self.genre_option_by_value[config.GENRE_CONTEXT])
        self.genre_menu = ctk.CTkOptionMenu(
            self.flavour_frame,
            width=MENU_WIDTH_NARROW,
            dynamic_resizing=False,
            values=list(self.genre_by_option),
            variable=self.genre_var
        )
        self.genre_menu.grid(row=0, column=2)

        # =========================================
        # Max Batch Size
        # =========================================
        ctk.CTkLabel(self.configuration_frame, text=i18n.t("label.max_batch_size"), anchor="w", font=config.FONT_HEADING) \
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

        self.max_batch_size_entry = ctk.CTkEntry(
            self.max_batch_size_frame,
            width=VALUE_LABEL_WIDTH,
            font=config.FONT_TEXT
        )
        self.max_batch_size_entry.insert(0, str(config.MAX_BATCH_SIZE))
        self.max_batch_size_entry.bind("<Return>", self.on_max_batch_size_entry_changed)
        self.max_batch_size_entry.bind("<FocusOut>", self.on_max_batch_size_entry_changed)
        self.max_batch_size_entry.pack(side="left", padx=(10, 5))

        ctk.CTkLabel(self.max_batch_size_frame, text=i18n.t("label.chars_unit"), font=config.FONT_TEXT).pack(side="left")

        # =========================================
        # Review terminology before translating (once)
        # =========================================
        self.pause_after_terminology_var = ctk.BooleanVar(value=config.PAUSE_AFTER_TERMINOLOGY)
        self.pause_after_terminology_checkbox = ctk.CTkCheckBox(
            self.configuration_frame,
            font=config.FONT_TEXT,
            text=i18n.t("option.review_terminology"),
            variable=self.pause_after_terminology_var
        )
        self.pause_after_terminology_checkbox.grid(row=9, column=1, sticky="w", padx=(0, 20), pady=5)

        # =========================================
        # Mock Mode Switch
        # =========================================
        self.mock_mode_var = ctk.BooleanVar(value=config.MOCK_MODE)
        self.mock_switch = ctk.CTkSwitch(
            self.configuration_frame,
            font=config.FONT_TEXT,
            text=i18n.t("option.simulate_only"),
            variable=self.mock_mode_var,
            command=self.on_mock_mode_changed,
            progress_color=config.RED,
            fg_color=config.GREY
        )
        self.mock_switch.grid(row=10, column=1, sticky="w", padx=(0, 20), pady=(5, 20))

        # =========================================
        # Prepare / Start / Reconfigure / Cancel Buttons
        # =========================================
        self.start_frame = ctk.CTkFrame(self.monitoring_frame, fg_color="transparent")
        self.start_frame.pack(padx=20, pady=20)

        self.main_button = ctk.CTkButton(
            self.start_frame,
            text=i18n.t("button.prepare"),
            command=self.prepare,
            width=BIG_BUTTON_WIDTH,
            height=BIG_BUTTON_HEIGHT,
            font=BIG_BUTTON_FONT,
            corner_radius=BIG_BUTTON_CORNER_RADIUS,
            border_width=BIG_BUTTON_BORDER_WIDTH
        )
        self.main_button.pack(side="left")

        self.main_button_default_color = self.main_button.cget("fg_color")
        self.main_button_default_hover_color = self.main_button.cget("hover_color")
        self.main_button_default_text_color = self.main_button.cget("text_color")
        self.main_button_tooltip = TOOLTIP_PREPARE  # follows the button's role, see set_main_button_role

        # Only visible after a successful preparation (see show_reconfigure_button)
        self.reconfigure_button = ctk.CTkButton(
            self.start_frame,
            text=i18n.t("button.reconfigure"),
            fg_color=config.theme_extras["colors"]["INK_LIGHT"],
            command=self.reconfigure,
            width=BIG_BUTTON_WIDTH,
            height=BIG_BUTTON_HEIGHT,
            font=BIG_BUTTON_FONT,
            corner_radius=BIG_BUTTON_CORNER_RADIUS,
            border_width=BIG_BUTTON_BORDER_WIDTH
        )

        # =========================================
        # Batch status bars and Stats Info Box
        # (hidden until the batches are known)
        # =========================================
        self.bars_frame = ctk.CTkFrame(self.monitoring_frame, fg_color="transparent")

        # Stats Info Box: a framed "card" with one grid row per stat (name | value), values are set in show_bars
        self.stats_frame = ctk.CTkFrame(
            self.bars_frame,
            fg_color=config.theme_extras["colors"]["PARCHMENT_LIGHT"],
            border_width=2,
            border_color=config.theme_extras["colors"]["INK_LIGHT"],
            corner_radius=8
        )
        self.stats_frame.pack(fill="x", pady=(0, 10))

        self.stats_grid = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.stats_grid.pack(anchor="w", padx=15, pady=10)

        self.chars_name_label = ctk.CTkLabel(self.stats_grid, text=i18n.t("stats.chars"), anchor="w", font=config.FONT_HEADING, text_color=config.theme_extras["colors"]["INK_CONTRAST"])
        self.chars_name_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.chars_value_label = ctk.CTkLabel(self.stats_grid, text="", anchor="w", font=config.FONT_TEXT, text_color=config.theme_extras["colors"]["INK_CONTRAST"])
        self.chars_value_label.grid(row=0, column=1, sticky="w")

        self.batches_name_label = ctk.CTkLabel(self.stats_grid, text=i18n.t("stats.batches"), anchor="w", font=config.FONT_HEADING, text_color=config.theme_extras["colors"]["INK_CONTRAST"])
        self.batches_name_label.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.batches_value_label = ctk.CTkLabel(self.stats_grid, text="", anchor="w", font=config.FONT_TEXT, text_color=config.theme_extras["colors"]["INK_CONTRAST"])
        self.batches_value_label.grid(row=1, column=1, sticky="w")

        # Only shown when there are Review Items (see show_bars)
        self.review_name_label = ctk.CTkLabel(
            self.stats_grid, text=i18n.t("stats.review_items"), anchor="w",
            text_color=config.MAGENTA, font=config.FONT_HEADING
        )
        self.review_name_label.grid(row=2, column=0, sticky="w", padx=(0, 10))
        self.review_value_label = ctk.CTkLabel(
            self.stats_grid, text="", anchor="w",
            text_color=config.MAGENTA, font=config.FONT_HEADING
        )
        self.review_value_label.grid(row=2, column=1, sticky="w")
        self.review_name_label.grid_remove()
        self.review_value_label.grid_remove()

        self.review_show_button = ctk.CTkButton(
            self.stats_grid,
            text=i18n.t("button.show"),
            width=60,
            height=24,
            command=self.show_review_items
        )
        self.review_show_button.grid(row=2, column=2, sticky="w", padx=(10, 0))
        self.review_show_button.grid_remove()

        # Terminology Progress Bar
        self.terminology_bar = ui_widgets.BatchStatusBar(
            self.bars_frame,
            i18n.t("stats.terminology"),
            on_clear=self.confirm_clear_terminology
        )
        self.terminology_bar.pack(fill="x", pady=(0, 10))

        # Terminology Progress Bar
        self.translation_bar = ui_widgets.BatchStatusBar(
            self.bars_frame,
            i18n.t("stats.translation"),
            on_clear=self.confirm_clear_translation
        )
        self.translation_bar.pack(fill="x")


        # =========================================
        # Log Output Window
        # =========================================
        self.log_popout_button = ctk.CTkButton(
            self.monitoring_frame,
            text=i18n.t("button.pop_out_log"),
            width=100,
            command=lambda: self.log_viewer.show()
        )
        self.log_popout_button.pack(padx=20, pady=(10, 0), anchor="e")


        # =========================================
        # Log Output Window
        # =========================================
        self.log_window = ui_widgets.LogTextbox(self.monitoring_frame, width=600, height=300)
        self.log_window.pack(padx=20, pady=20, fill="both", expand=True)
        self.log_viewer = ui_dialogs.LogViewerDialog(self)
        self.log_viewer_was_visible = False


        # =========================================
        # Enable only the UI elements that are relevant first
        # =========================================
        self.locked_look = ui_widgets.LockedLook()
        self.disable_configuration_controls(tint_frame=False)
        self.file_button.configure(state="normal")
        self.output_dir_button.configure(state="normal")
        self.output_dir_reset_button.configure(state="normal")

        # =========================================
        # Some initialization of dialog-relevant queues
        # =========================================
        self.current_request = None
        self.current_confirm_dialog = None
        self.cancel_event = threading.Event()
        self.is_busy = False  # True while preparing or running, see prepare()/run_translation()

        # =========================================
        # Hover info texts
        # =========================================
        self.attach_tooltips()

        # =========================================
        # Now go for it!
        # =========================================
        self.show_status(i18n.t("status.waiting_for_configuration"))
        self.render_dialog_requests()


    # ===========================================
    # Function: Attach Tooltips
    # Hover info texts of the UI elements, all in one place.
    # A function instead of a text is evaluated on each hover, for texts that change (like paths)
    # ===========================================
    def attach_tooltips(self):

        def tip(widget, text):
            ui_widgets.Tooltip(widget, text)

        # Banner
        tip(self.settings_button, i18n.t("tooltip.settings"))
        tip(self.help_button, i18n.t("tooltip.help"))

        # Configuration
        tip(self.file_button, i18n.t("tooltip.input_file"))
        tip(self.file_label, lambda: str(self.selected_file) if self.selected_file else i18n.t("tooltip.no_file_selected"))
        tip(self.output_dir_button, i18n.t("tooltip.output_folder"))
        tip(self.output_dir_reset_button, i18n.t("tooltip.reset_output_folder"))
        tip(self.output_dir_label, lambda: str(self.selected_output_dir or config.USER_DATA_DIR / config.OUTPUT_FOLDER_NAME))

        input_type_tip = i18n.t("tooltip.input_type")
        tip(self.radio_input_type_babele, input_type_tip)
        tip(self.radio_input_type_localization, input_type_tip)

        language_tip = i18n.t("tooltip.language")
        tip(self.source_language_menu, language_tip)
        tip(self.target_language_menu, language_tip)

        flavour_tip = i18n.t("tooltip.flavour")
        tip(self.game_system_menu, flavour_tip)
        tip(self.genre_menu, flavour_tip)

        tip(self.module_name_entry, i18n.t("tooltip.module_name"))

        batch_size_tip = i18n.t("tooltip.max_batch_size")
        tip(self.max_batch_size_slider, batch_size_tip)
        tip(self.max_batch_size_entry, batch_size_tip)

        tip(self.pause_after_terminology_checkbox, i18n.t("tooltip.review_terminology"))
        tip(self.mock_switch, i18n.t("tooltip.simulate_only"))

        # Main buttons
        tip(self.main_button, lambda: i18n.t(self.main_button_tooltip))
        tip(self.reconfigure_button, i18n.t("tooltip.reconfigure"))

        # Monitoring
        tip(self.terminology_bar.clear_button, i18n.t("tooltip.clear_terminology"))
        tip(self.translation_bar.clear_button, i18n.t("tooltip.clear_translation"))
        tip(self.review_show_button, i18n.t("tooltip.show_review_items"))
        tip(self.log_popout_button, i18n.t("tooltip.pop_out_log"))

        # Status bar: the full text, in case it is truncated
        tip(self.status_label, lambda: self.status_label.cget("text"))


    # ===========================================
    # Function: Select File
    # Generated a UI File Picker for selecting the Input File
    # ===========================================
    def select_file(self):
        filename = filedialog.askopenfilename(
            title=i18n.t("dialog.select_file_title"),
            filetypes=[(i18n.t("dialog.json_files"), "*.json")],
            initialdir=str(self.selected_file.parent) if self.selected_file else None
        )

        if not filename:
            return

        previous_file = self.selected_file
        self.set_input_file(Path(filename))

        # A newly picked (different) file is a first run, so the terminology review is on by default
        if Path(filename) != previous_file:
            self.pause_after_terminology_var.set(True)


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
            title=i18n.t("dialog.select_output_title"),
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
            ui_dialogs.HintDialog(self, message=i18n.t("hint.languages_must_differ"))
            return

        config.INPUT_TYPE = self.input_type_var.get()
        config.MODULE_NAME = self.module_name_entry.get().strip()
        config.BASE_OUTPUT_DIR = self.selected_output_dir  # None => fall back to USER_DATA_DIR
        config.SOURCE_LANGUAGE = self.language_by_option[self.source_language_var.get()]
        config.TARGET_LANGUAGE = self.language_by_option[self.target_language_var.get()]
        config.GAME_SYSTEM_CONTEXT = self.game_system_by_option[self.game_system_var.get()]
        config.GENRE_CONTEXT = self.genre_by_option[self.genre_var.get()]
        self.on_max_batch_size_entry_changed()
        config.MAX_BATCH_SIZE = int(self.max_batch_size_entry.get())
        config.PAUSE_AFTER_TERMINOLOGY = self.pause_after_terminology_var.get()

        fn.adapt_file_paths()
        self.persist_settings()

        self.disable_configuration_controls()
        self.show_status(i18n.t("status.preparing"))

        self.is_busy = True

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
    # and "Reconfigure" allows to go back
    # ===========================================
    def enter_prepared_state(self, result):
        self.prepared_result = result
        self.set_main_button_role(i18n.t("button.start"), self.run_translation, TOOLTIP_START, color=config.GREEN)
        self.show_reconfigure_button()
        self.show_bars(result["analysis"])
        self.update_clear_buttons(result["analysis"])
        self.show_status(i18n.t("status.ready_to_start"))


    # ===========================================
    # Function: Reset Preparation
    # Goes back from the prepared state to the initial "choose" state
    # ===========================================
    def reconfigure(self):
        self.prepared_result = None
        self.hide_reconfigure_button()
        self.set_main_button_role(i18n.t("button.prepare"), self.prepare, TOOLTIP_PREPARE)
        self.enable_configuration_controls()
        self.hide_bars()
        self.show_status(i18n.t("status.waiting_for_configuration"))


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
    def confirm_clear(self, key, clear_function):

        def on_yes():
            clear_function()
            analysis = fn.analyze_progress_info()
            self.show_bars(analysis)
            self.update_clear_buttons(analysis)

        ui_dialogs.confirm_yes_no(
            key,
            on_yes=on_yes,
            on_no=None
        )


    # ===========================================
    # Function: Confirm Clear Terminology
    # ===========================================
    def confirm_clear_terminology(self):
        self.confirm_clear(
            key="confirm.clear_terminology",
            clear_function=fn.clear_terminology
        )


    # ===========================================
    # Function: Confirm Clear Translation
    # ===========================================
    def confirm_clear_translation(self):
        self.confirm_clear(
            key="confirm.clear_translation",
            clear_function=fn.clear_translation
        )


    # ===========================================
    # Function: Run Translation
    # Starts the main worker thread (translation) asynchronously
    # ===========================================
    def run_translation(self) -> bool:

        # Pre-flight check: Do we have an API key on board?
        if not config.MOCK_MODE and fn.is_api_key_required() and not security.has_api_key():
            self.open_settings(callback=self.run_translation)
            return False

        self.cancel_event.clear()
        self.hide_reconfigure_button()
        self.set_clear_buttons_enabled(False)

        if config.INPUT_FILE is None:
            self.LOGGER("Please select an input file first.", config.TAG_ERROR)
            return False

        self.disable_configuration_controls()

        # The main button turns into the Cancel button while running
        self.set_main_button_role(i18n.t("button.cancel"), self.cancel, TOOLTIP_CANCEL, color=config.YELLOW, text_color=config.theme_extras["colors"]["INK_CONTRAST"])
        self.show_status(i18n.t("status.running"))

        self.is_busy = True

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

        self.is_busy = False

        if outcome["outcome"] == config.OUTCOME_SUCCESS:
            self.enter_prepared_state(outcome["result"])
            return

        # Nothing has been prepared, so back to the start
        self.show_outcome_message(outcome)
        self.reconfigure()
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

        self.is_busy = False

        self.show_outcome_message(outcome)

        # The progress is persisted, whatever happened, so continue from it
        self.return_to_prepared_state()

        if outcome["outcome"] == config.OUTCOME_SUCCESS:
            self.show_results() # needs to be called after return_to_prepared_state, so that results can't get overwritten by the "Ready to start." status message
            fn.play_sound_completed()
        elif outcome["outcome"] == config.OUTCOME_PAUSED:
            self.show_terminology_review()
            fn.play_sound_completed()
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
        self.suspend_log_viewer()

        def answer(is_yes):
            self.current_request = None
            self.current_confirm_dialog = None
            self.restore_log_viewer()

            if "response_queue" in request:
                request["response_queue"].put(config.YES if is_yes else config.NO)
            else:
                callback = request["on_yes"] if is_yes else request["on_no"]

                if callback:
                    callback()

        def on_show_log():
            self.current_confirm_dialog.grab_release()
            self.log_viewer.show()

        self.current_confirm_dialog = ui_dialogs.ConfirmDialog(
            self,
            question=request["question"],
            on_yes=lambda: answer(True),
            on_no=lambda: answer(False),
            on_show_log=on_show_log
        )


    # ===========================================
    # Function: Show Review Items
    # Opens the pop-out view with the Review Items collected so far
    # ===========================================
    def show_review_items(self):
        review_items = fn.load_json_input(config.PROGRESS_REVIEW_ITEMS_FILE)
        ui_dialogs.ReviewItemsDialog(self, review_items)


    # ===========================================
    # Function: Suspend Log Viewer
    # A pending confirmation is modal, so a visible (non-modal) log viewer would be unresponsive.
    # It is hidden while the confirmation is pending and brought back by restore_log_viewer()
    # ===========================================
    def suspend_log_viewer(self):
        self.log_viewer_was_visible = bool(self.log_viewer.winfo_viewable())

        if self.log_viewer_was_visible:
            self.log_viewer.hide()


    # ===========================================
    # Function: Restore Log Viewer
    # ===========================================
    def restore_log_viewer(self):
        if self.log_viewer_was_visible:
            self.log_viewer_was_visible = False
            self.log_viewer.show()


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
        previous_state = self.max_batch_size_entry.cget("state")
        self.max_batch_size_entry.configure(state="normal")
        self.max_batch_size_entry.delete(0, "end")
        self.max_batch_size_entry.insert(0, str(int(round(value))))
        self.max_batch_size_entry.configure(state=previous_state)

    def on_max_batch_size_entry_changed(self, event=None):
        try:
            value = int(self.max_batch_size_entry.get().strip())
        except ValueError:
            value = int(self.max_batch_size_slider.get())  # invalid input: revert to the slider's last value

        value = fn.clamp(value, 500, 100000)

        self.max_batch_size_entry.delete(0, "end")
        self.max_batch_size_entry.insert(0, str(value))
        self.max_batch_size_slider.set(value)


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
        height = int(event.height * DECO_IMAGE_HEIGHT_RATIO)
        width = int(height * self.deco_source_image.width / self.deco_source_image.height)

        if (width, height) == self.deco_image_size:
            return

        self.deco_image_size = (width, height)
        self.deco_image = ctk.CTkImage(light_image=self.deco_source_image, size=self.deco_image_size)
        self.deco_image_label.configure(image=self.deco_image)

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
    def disable_configuration_controls(self, tint_frame=True):

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
        self.max_batch_size_entry.configure(state="disabled")
        self.set_configuration_panel_locked(True, tint_frame=tint_frame)
        self.set_controls_locked(True)
        self.pause_after_terminology_checkbox.configure(state="disabled")

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
        self.max_batch_size_entry.configure(state="normal")
        self.configuration_frame.configure()
        self.set_configuration_panel_locked(False)
        self.set_controls_locked(False)
        self.pause_after_terminology_checkbox.configure(state="normal")


    # ===========================================
    # Function: Set Configuration Panel Locked
    # Disabled CTk widgets barely look different, so the panel is tinted and its labels are dimmed
    # ===========================================
    def set_configuration_panel_locked(self, locked, tint_frame=True):
        if tint_frame:
            self.locked_look.apply(self.configuration_frame, locked)

        for child in self.configuration_frame.winfo_children():
            if isinstance(child, ctk.CTkLabel) and child is not self.deco_image_label:
                self.locked_look.apply(child, locked)


    # ===========================================
    # Function: Set Controls Locked
    # Recolors (locked) or restores (unlocked) the configuration controls.
    # The main button is left out, because it is colored by its role
    # ===========================================
    def set_controls_locked(self, locked):
        controls = [
            self.file_button, self.output_dir_button, self.output_dir_reset_button,
            self.radio_input_type_babele, self.radio_input_type_localization,
            self.module_name_entry, self.mock_switch, self.pause_after_terminology_checkbox,
            self.source_language_menu, self.target_language_menu,
            self.game_system_menu, self.genre_menu,
            self.max_batch_size_slider
        ]

        for control in controls:
            self.locked_look.apply(control, locked)


    # ===========================================
    # Function: Cancel
    # Used by the main button while running.
    # Effective at the next Batch boundary, so a running API call has to be waited out
    # ===========================================
    def cancel(self):
        self.cancel_event.set()
        self.set_main_button_role(i18n.t("button.please_wait"), self.cancel, TOOLTIP_WAITING, color=config.RED, state="disabled")

        # A pending confirm dialog has to be released as well, because the worker thread
        # blocks while waiting for the answer
        if self.current_confirm_dialog is not None:
            self.current_confirm_dialog.destroy()
            self.current_confirm_dialog = None
            self.restore_log_viewer()

        if self.current_request is not None and "response_queue" in self.current_request:
            self.current_request["response_queue"].put(config.CANCEL)
            self.current_request = None


    # ===========================================
    # Function: Set Main Button Role
    # Sets text, command, state, colors and hover info of the main button in one go
    # (color/text_color None => back to the default colors)
    # ===========================================
    def set_main_button_role(self, text, command, tooltip, color=None, text_color=None, state="normal"):
        self.main_button_tooltip = tooltip
        self.main_button.configure(
            text=text,
            command=command,
            state=state,
            fg_color=color or self.main_button_default_color,
            hover_color=color or self.main_button_default_hover_color,
            text_color=text_color or self.main_button_default_text_color
        )


    # ===========================================
    # Function: Show Reconfigure Button
    # ===========================================
    def show_reconfigure_button(self):
        self.reconfigure_button.pack(side="left", padx=(0, 10), before=self.main_button)


    # ===========================================
    # Function: Hide Reconfigure Button
    # ===========================================
    def hide_reconfigure_button(self):
        self.reconfigure_button.pack_forget()


    # ===========================================
    # Function: Localized Error Message
    # The message of an expected error in the UI language (the log gets the English one)
    # ===========================================
    def localized_error_message(self, outcome):
        return i18n.t(outcome["message_key"], **outcome["message_params"])


    # ===========================================
    # Function: Show Outcome Message
    # Tells the user what happened, depending on how a phase (preparing/running) ended
    # ===========================================
    def show_outcome_message(self, outcome):

        kind = outcome["outcome"]

        if kind == config.OUTCOME_CANCELLED:
            self.LOGGER("Cancelled by user.", config.TAG_WARNING)
            fn.play_sound_phase_complete()

        elif kind == config.OUTCOME_DECLINED:
            self.LOGGER("Aborted by user.", config.TAG_WARNING)

        elif kind == config.OUTCOME_EXPECTED_ERROR:
            self.LOGGER(outcome["message"], config.TAG_ERROR)
            ui_dialogs.HintDialog(self, message=self.localized_error_message(outcome))

        elif kind == config.OUTCOME_UNEXPECTED_ERROR:
            # The log stays English (for bug reports), the dialog is localized
            self.LOGGER(f"An unexpected error occurred:\n{outcome['message']}", config.TAG_ERROR)
            print(outcome["details"])  # full traceback to the console
            ui_dialogs.ErrorDialog(self, message=i18n.t("dialog.unexpected_error", message=outcome["message"]))


    # ===========================================
    # Function: Show Outcome Status
    # One-line status for a phase that did not end successfully
    # ===========================================
    def show_outcome_status(self, outcome):

        kind = outcome["outcome"]

        if kind == config.OUTCOME_CANCELLED:
            self.show_status(i18n.t("status.cancelled"))

        elif kind == config.OUTCOME_DECLINED:
            self.show_status(i18n.t("status.aborted"))

        elif kind == config.OUTCOME_EXPECTED_ERROR:
            self.show_status(i18n.t("status.error", message=self.localized_error_message(outcome).splitlines()[0]))

        elif kind == config.OUTCOME_UNEXPECTED_ERROR:
            self.show_status(i18n.t("status.unexpected_error"))


    # ===========================================
    # Function: Show Status
    # Shows a message in the status bar (and hides the results button, which only belongs to results)
    # ===========================================
    def show_status(self, message):
        self.status_label.configure(text=message)
        self.open_folder_button.pack_forget() # This is the default, to make sure that the button never stays visible longer than needed


    # ===========================================
    # Function: Show Folder Link
    # Shows the status bar button that opens <folder> in the file manager
    # ===========================================
    def show_folder_link(self, text, folder):
        self.open_folder_button.configure(text=text, command=lambda: fn.open_folder(folder))
        self.open_folder_button.pack(side="right", padx=20, before=self.status_label)


    # ===========================================
    # Function: Show Terminology Review
    # The run was paused after terminology: tells the user how to continue.
    # The option is a one-shot, so it is reset here, otherwise the next Start would pause again
    # ===========================================
    def show_terminology_review(self):
        self.pause_after_terminology_var.set(False)
        config.PAUSE_AFTER_TERMINOLOGY = False
        settings.update_settings({"pause_after_terminology": False})

        self.show_status(i18n.t("status.terminology_review", file=config.TERMINOLOGY_FILE.name))
        self.show_folder_link(i18n.t("button.open_terminology_folder"), config.TERMINOLOGY_DIR)


    # ===========================================
    # Function: Show Results
    # Announces the output of a successful run in the status bar
    # ===========================================
    def show_results(self):
        self.show_status(i18n.t("status.translation_completed", file=config.OUTPUT_FILE.name))
        self.show_folder_link(i18n.t("button.open_output_folder"), config.OUTPUT_DIR)


    # ===========================================
    # Function: Log Message
    # Writes the message passed to the inline log viewer
    # ===========================================
    def log_message(self, message, tag=""):
        self.log_window.append(message, tag)
        self.log_viewer.append(message, tag)


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
    # Function: Open Help
    #
    # ===========================================
    def open_help(self):
        ui_dialogs.HelpDialog(self)


    # ===========================================
    # Function: Persist Settings
    # Saves the current selections to the settings file (called when a translation starts)
    # ===========================================
    def persist_settings(self):
        settings.update_settings({
            "base_output_dir": str(config.BASE_OUTPUT_DIR) if config.BASE_OUTPUT_DIR else None,
            "input_file": str(config.INPUT_FILE),
            "input_type": config.INPUT_TYPE,
            "module_name": config.MODULE_NAME,
            "source_language_code": config.SOURCE_LANGUAGE["code"],
            "target_language_code": config.TARGET_LANGUAGE["code"],
            "game_system_context": config.GAME_SYSTEM_CONTEXT,
            "genre_context": config.GENRE_CONTEXT,
            "pause_after_terminology": config.PAUSE_AFTER_TERMINOLOGY,
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

        # LLM connection: independent of everything else (empty/missing => defaults from config)
        config.API_BASE_URL = saved.get("api_base_url") or config.OPENAI_BASE_URL
        config.API_KEY_REQUIRED = saved.get("api_key_required", True)
        config.LLM_MODEL = saved.get("llm_model") or config.LLM_MODEL

        config.HIDE_TOOLTIPS = bool(saved.get("hide_tooltips", False))

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
        if game_system_context in self.game_system_option_by_value:
            self.game_system_var.set(self.game_system_option_by_value[game_system_context])

        genre_context = saved.get("genre_context")
        if genre_context in self.genre_option_by_value:
            self.genre_var.set(self.genre_option_by_value[genre_context])

        self.pause_after_terminology_var.set(bool(saved.get("pause_after_terminology", True)))

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

# (Repeated on purpose: the first call ran before the app's log window existed. It is idempotent)
fn.init_system_dirs()
app.restore_settings()

# Finally, run it!
app.mainloop()

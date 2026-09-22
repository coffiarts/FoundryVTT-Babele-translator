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
        # Settings button
        # =========================================
        self.settings_button = ctk.CTkButton(
            self, text="⚙ Settings", command=self.open_settings
        )
        self.settings_button.pack(padx=20, pady=(10, 5))

        # =========================================
        # Input File picker
        # =========================================
        self.selected_file = None

        self.file_button = ctk.CTkButton(
            self,
            text="Select Input File",
            command=self.select_file
        )

        self.file_button.pack(padx=20, pady=(20, 5))

        self.file_label = ctk.CTkLabel(
            self,
            text="No file selected",
            font=("Arial", 18, "bold")
        )

        self.file_label.pack(padx=20, pady=(0, 20))

        # =========================================
        # Output folder picker (optional)
        # =========================================
        self.selected_output_dir = None
        self.output_dir_default_text = "Default: user data folder"

        self.output_dir_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.output_dir_frame.pack(padx=20, pady=(0, 5))

        self.output_dir_button = ctk.CTkButton(
            self.output_dir_frame,
            text="Select Output Folder (optional)",
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
            self,
            text=self.output_dir_default_text,
            font=("Arial", 14)
        )
        self.output_dir_label.pack(padx=20, pady=(0, 20))

        # =========================================
        # Input type selector
        # =========================================
        self.input_type_frame = ctk.CTkFrame(self)

        self.input_type_frame.pack(
            padx=20,
            pady=5
        )

        self.input_type_var = ctk.StringVar(
            value=config.INPUT_TYPE_BABELE
        )

        self.input_type_var.trace_add(
            "write",
            self.on_input_type_changed
        )

        self.radio_input_type_babele = ctk.CTkRadioButton(
            self.input_type_frame,
            text=config.INPUT_TYPE_BABELE,
            variable=self.input_type_var,
            value=config.INPUT_TYPE_BABELE
        )

        self.radio_input_type_babele.pack(
            side="left", padx=(0, 20)
        )

        self.radio_input_type_localization = ctk.CTkRadioButton(
            self.input_type_frame,
            text=config.INPUT_TYPE_LOCALIZATION,
            variable=self.input_type_var,
            value=config.INPUT_TYPE_LOCALIZATION
        )

        self.radio_input_type_localization.pack(
            side="left"
        )

        # =========================================
        # Language selection
        # =========================================
        self.language_options = [
            f"{lang['code']}: {lang['name']}" for lang in config.SUPPORTED_LANGUAGES
        ]
        self.language_by_option = {
            option: lang for option, lang in zip(self.language_options, config.SUPPORTED_LANGUAGES)
        }

        self.language_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.language_frame.pack(padx=20, pady=(15, 5))

        self.source_language_var = ctk.StringVar(
            value=f"{config.SOURCE_LANGUAGE['code']}: {config.SOURCE_LANGUAGE['name']}"
        )
        self.source_language_menu = ctk.CTkOptionMenu(
            self.language_frame,
            values=self.language_options,
            variable=self.source_language_var
        )
        self.source_language_menu.pack(side="left")

        ctk.CTkLabel(self.language_frame, text="  →  ", font=("Arial", 16, "bold")).pack(side="left")

        self.target_language_var = ctk.StringVar(
            value=f"{config.TARGET_LANGUAGE['code']}: {config.TARGET_LANGUAGE['name']}"
        )
        self.target_language_menu = ctk.CTkOptionMenu(
            self.language_frame,
            values=self.language_options,
            variable=self.target_language_var
        )
        self.target_language_menu.pack(side="left")

        # =========================================
        # Module name suggestion (editable)
        # =========================================
        self.module_name_label = ctk.CTkLabel(
            self,
            text="Module name (overwrite as needed)",
            font=("Arial", 18, "bold")
        )

        self.module_name_label.pack(padx=20, pady=(20, 0))

        self.module_name_entry = ctk.CTkEntry(
            self,
            width=300,
            font=("Arial", 14, "bold")
        )

        self.module_name_entry.pack(padx=20, pady=5, fill="x")

        self.module_name_entry.insert(0, "(Please pick a file first)")

        # =========================================
        # Max Batch Size
        # =========================================
        self.max_batch_size_label = ctk.CTkLabel(
            self,
            text=f"Max Batch Size: {config.MAX_BATCH_SIZE:,} chars",
            font=("Arial", 14, "bold")
        )
        self.max_batch_size_label.pack(padx=20, pady=(15, 0))

        self.max_batch_size_slider = ctk.CTkSlider(
            self,
            from_=500,
            to=100000,
            number_of_steps=199,
            command=self.on_max_batch_size_changed
        )
        self.max_batch_size_slider.set(config.MAX_BATCH_SIZE)
        self.max_batch_size_slider.pack(padx=20, pady=(0, 10), fill="x")


        # =========================================
        # Mock Mode Switch
        # =========================================
        self.mock_mode_var = ctk.BooleanVar(value=config.MOCK_MODE)
        self.mock_switch = ctk.CTkSwitch(
            self,
            text="Simulate only",
            variable=self.mock_mode_var,
            command=self.on_mock_mode_changed,
            progress_color="red",
            fg_color="gray"
        )
        self.mock_switch.pack(padx=20, pady=20)

        # =========================================
        # Prepare / Start / Reset / Cancel Buttons
        # =========================================
        self.start_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.start_frame.pack(padx=20, pady=20)

        self.main_button = ctk.CTkButton(
            self.start_frame,
            text="Prepare",
            command=self.prepare
        )
        self.main_button.pack(side="left")

        # Only visible after a successful preparation (see show_reset_button)
        self.reset_button = ctk.CTkButton(
            self.start_frame,
            text="Reset",
            fg_color="gray",
            command=self.reset_preparation
        )

        # =========================================
        # Batch status bars (hidden until the batches are known)
        # =========================================
        self.bars_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.terminology_bar = ui_widgets.BatchStatusBar(
            self.bars_frame,
            "Terminology",
            on_clear=self.confirm_clear_terminology
        )
        self.terminology_bar.pack(fill="x", pady=(0, 10))

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
            self,
            text="Pop Out Log",
            width=100,
            command=lambda: ui_dialogs.LogViewerDialog(self, self.log_window.get("1.0", "end"))
        )
        self.log_popout_button.pack(padx=20, pady=(10, 0), anchor="e")

        self.log_window = ctk.CTkTextbox(self, width=600, height=300, fg_color="black", text_color="white")


        # =========================================
        # Log Output Window
        # =========================================
        self.log_window = ctk.CTkTextbox(self, width=600, height=300, fg_color="black", text_color="white")
        self.log_window.tag_config(config.TAG_ERROR, foreground="red")
        self.log_window.tag_config(config.TAG_SUCCESS, foreground="green")
        self.log_window.tag_config(config.TAG_WARNING, foreground="yellow")
        self.log_window.tag_config(config.TAG_INFO, foreground="blue")
        self.log_window.tag_config(config.TAG_QUESTION, foreground="magenta")
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

        config.INPUT_TYPE = self.input_type_var.get()
        config.MODULE_NAME = self.module_name_entry.get().strip()
        config.BASE_OUTPUT_DIR = self.selected_output_dir  # None => fall back to USER_DATA_DIR
        config.SOURCE_LANGUAGE = self.language_by_option[self.source_language_var.get()]
        config.TARGET_LANGUAGE = self.language_by_option[self.target_language_var.get()]
        config.MAX_BATCH_SIZE = int(round(self.max_batch_size_slider.get()))

        fn.adapt_file_paths()
        self.persist_settings()

        self.disable_configuration_controls()

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

        self.main_button.configure(text="Start", command=self.run_translation, state="normal")
        self.show_reset_button()
        self.show_bars(result["analysis"])
        self.update_clear_buttons(result["analysis"])


        # ===========================================
    # Function: Reset Preparation
    # Goes back from the prepared state to the initial "choose" state
    # ===========================================
    def reset_preparation(self):
        self.prepared_result = None

        self.hide_reset_button()
        self.main_button.configure(text="Prepare", command=self.prepare)
        self.enable_configuration_controls()
        self.hide_bars()


    # ===========================================
    # Function: Show Bars
    # Renders the batch status bars from the analysis delivered by the preparation
    # ===========================================
    def show_bars(self, analysis):
        batches = analysis["batches"]

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
    def batches_changed(self, batches):
        self.after(
            0,
            lambda: self.show_bars({"batches": batches})
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
        self.main_button.configure(text="Cancel", command=self.cancel, state="normal")

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
        self.max_batch_size_label.configure(text=f"Max Batch Size: {int(round(value)):,} chars")


    # ===========================================
    # Function: On Mock Mode Changed
    # Gets alerted whenever a the Mock Mode Switch is toggled
    # ===========================================
    def on_mock_mode_changed(self):
        config.MOCK_MODE = bool(self.mock_mode_var.get())
        # self.LOGGER(f"MOCK_MODE = {config.MOCK_MODE}")


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
        self.max_batch_size_slider.configure(state="normal")


    # ===========================================
    # Function: Cancel
    # Used by the main button while running.
    # Effective at the next Batch boundary, so a running API call has to be waited out
    # ===========================================
    def cancel(self):
        self.cancel_event.set()
        self.main_button.configure(text="Please wait for batch to complete ...", state="disabled")

        # A pending confirm dialog has to be released as well, because the worker thread
        # blocks while waiting for the answer
        if self.current_confirm_dialog is not None:
            self.current_confirm_dialog.destroy()
            self.current_confirm_dialog = None

        if self.current_request is not None and "response_queue" in self.current_request:
            self.current_request["response_queue"].put(config.CANCEL)
            self.current_request = None


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

fn.init_system_dirs()
app.restore_settings()

# Finally, run it!
app.mainloop()

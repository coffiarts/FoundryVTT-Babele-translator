import ct4f_config as config
import ct4f_translator as translator
import ct4f_translator_dialogs as translator_dialogs
import ct4f_ui_dialogs as ui_dialogs
import ct4f_core_functions as fn
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

        self.title("coffiarts' Translator for Foundry VTT")
        self.iconbitmap(fn.resource_path("assets/icon.ico"))
        self.calculate_window_dimensions(min_width=1000, min_height=700, factor=0.8)

        # =========================================
        # File picker
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
        # Start Translation Button
        # =========================================
        self.start_button = ctk.CTkButton(
            self,
            text="Start Translation",
            command=self.prepare_start
        )
        self.start_button.pack(padx=20, pady=20)

        # =========================================
        # Mock Mode Switch
        # =========================================
        self.mock_mode_var = ctk.BooleanVar(value=config.MOCK_MODE)
        self.mock_switch = ctk.CTkSwitch(
            self,
            text="Mock Mode",
            variable=self.mock_mode_var,
            command=self.on_mock_mode_changed,
            progress_color="red",
            fg_color="gray"
        )
        self.mock_switch.pack(padx=20, pady=20)

        # =========================================
        # Log Output Window
        # =========================================
        self.log_window = ctk.CTkTextbox(self, width=600, height=300, fg_color="black", text_color="white")
        self.log_window.tag_config(config.TAG_ERROR, foreground="red")
        self.log_window.tag_config(config.TAG_SUCCESS, foreground="green")
        self.log_window.tag_config(config.TAG_WARNING, foreground="yellow")
        self.log_window.tag_config(config.TAG_INFO, foreground="blue")
        self.log_window.tag_config(config.TAG_QUESTION, foreground="magenta")
        self.log_window.pack(padx=20, pady=20, fill="both", expand=False)


        # =========================================
        # Dynamic prompts (at bottom, initially hidden)
        # =========================================
        self.current_radio_buttons = []

        self.question_label = ctk.CTkLabel(
            self,
            text="",
            font=("Arial", 16, "bold")
        )
        self.show_question_label()

        self.text_answer_entry = ctk.CTkEntry(
            self,
            width=400
        )
        self.show_text_answer_entry()

        # Buttons Frame
        self.buttons_frame = ctk.CTkFrame(self)

        # Submit ("OK") Button
        self.submit_button = ctk.CTkButton(
            self.buttons_frame,
            text="OK",
            command=self.read_dialog_response
        )
        self.show_submit_button()

        # YES Button
        self.yes_button = ctk.CTkButton(
            self.buttons_frame,
            text="Yes",
            command=self.submit_yes
        )

        # NO Button
        self.no_button = ctk.CTkButton(
            self.buttons_frame,
            text="No",
            command=self.submit_no
        )

        # CANCEL Button
        self.cancel_button = ctk.CTkButton(
            self.buttons_frame,
            text="Cancel",
            command=self.cancel
        )

        # Set them all initially to invisible
        self.hide_cancel_button()
        self.hide_all_prompts()

        # =========================================
        # Now go for it!
        # =========================================
        self.current_request = None
        self.disable_configuration_controls()
        self.file_button.configure(state="normal")
        self.cancel_event = threading.Event()
        self.render_dialog_requests()

    # ===========================================
    # Function: Select File
    # Generated a UI File Picker for selecting the Input File
    # ===========================================
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="Select file to translate",
            filetypes=[("JSON files", "*.json")]
        )

        if not filename:
            return

        self.selected_file = Path(filename)

        config.INPUT_FILE = self.selected_file
        config.INPUT_FILE_NAME = self.selected_file.name

        self.file_label.configure(
            text=config.INPUT_FILE_NAME
        )

        self.enable_configuration_controls()

        self.refresh_module_name_suggestion()


    # ===========================================
    # Function: Prepare Start
    # Checks which run mode to apply, then delegates to the respective follow-up function
    # ===========================================
    def prepare_start(self):

        # Check for existing progress-info
        config.INPUT_TYPE = self.input_type_var.get()
        config.MODULE_NAME = self.module_name_entry.get().strip()
        fn.adapt_file_paths()

        progress_info = fn.analyze_progress_info()
        # self.LOGGER(f"progress_info:\n:{fn.to_prettified_json(progress_info)}")

        if progress_info is not None:

            self.init_visual_process_status()

            ui_dialogs.confirm_yes_no(
                question="Do you want to resume the incomplete process for this file?",
                on_yes=self.run_translation,
                on_no=self.start_from_scratch
            )

        else:

            self.run_translation()


    # ===========================================
    # Function: Initialize Visual Process Status
    # Visualizes the last state of an existing, resumable process
    # ===========================================
    def start_from_scratch(self):
        # TODO: reset_ui()
        # TODO: start_translation()
        self.run_translation()


    # ===========================================
    # Function: Run Translation
    # Starts the main worker thread (translation) asynchronously
    # ===========================================
    def run_translation(self) -> bool:
        self.cancel_event.clear()
        self.show_cancel_button()

        if config.INPUT_FILE is None:
            self.LOGGER("Please select an input file first.", config.TAG_ERROR)
            return False

        config.INPUT_TYPE = self.input_type_var.get()
        config.MODULE_NAME = self.module_name_entry.get().strip()

        self.disable_configuration_controls()

        threading.Thread(
            target=translator.run_translation,
            kwargs={
                "logger": self.log_message,
                "finished": self.translation_finished,
                "cancel_event": self.cancel_event
            },
            daemon=True
        ).start()

        return True


    # ===========================================
    # Function: Translation Finished
    # A callback invoked when start_translation() completes
    # Its main function is to reactivate the start button
    # ===========================================
    def translation_finished(self):
        self.after(
            0,
            lambda: self.reset_ui()
        )


    # ===========================================
    # Function: Reset UI
    # Restores the initial state before pressing
    # the "Start Translation" Button
    # ===========================================
    def reset_ui(self):
        self.hide_all_prompts()
        self.enable_configuration_controls()


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
            if request["type"] == config.PROMPT_TYPE_RADIO:
                self.current_request = request

                self.question_label.configure(
                    text=request["question"]
                )
                self.show_question_label()

                self.radio_var = ctk.StringVar()

                for option in request["options"]:
                    radio = ctk.CTkRadioButton(
                        self,
                        text=option,
                        variable=self.radio_var,
                        value=option
                    )
                    radio.pack(
                        padx=20,
                        anchor="w"
                    )

                    self.current_radio_buttons.append(radio)

                self.show_buttons_frame()
                self.show_submit_button()

            elif request["type"] == config.PROMPT_TYPE_YESNO:

                self.current_request = request

                self.question_label.configure(
                    text=request["question"]
                )

                self.show_question_label()
                self.show_buttons_frame()
                self.show_yesno_buttons()

            elif request["type"] == config.PROMPT_TYPE_TEXT:
                self.current_request = request

                self.question_label.configure(
                    text=request["question"]
                )

                self.show_question_label()
                self.show_text_answer_entry()
                self.show_buttons_frame()
                self.show_submit_button()

                self.text_answer_entry.focus()

            else:
                print("UNKNOWN REQUEST")

        self.after(50, self.render_dialog_requests)


    # ===========================================
    # Function: Process Dialog Response
    # Submits the current dialog response, delivers it to the waiting request,
    # and removes any temporary dialog controls from the UI.
    # ===========================================
    def read_dialog_response(self):

        if self.current_request is None:
            return

        if self.current_radio_buttons:
            answer = self.radio_var.get()

        else:
            answer = self.text_answer_entry.get().strip().upper()

        self.current_request["response_queue"].put(answer)

        self.text_answer_entry.delete(0, "end")

        self.hide_all_prompts()

        self.current_request = None

        for radio in self.current_radio_buttons:
            radio.destroy()
        self.current_radio_buttons.clear()


    # ===========================================
    # Function: On Input Type Changed
    # Gets alerted whenever a new INPUT_TYPE has selected
    # Ensures that the Module Name Suggestion gets reevaluated
    # ===========================================
    def on_input_type_changed(self, *args):
        self.refresh_module_name_suggestion()


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
        self.radio_input_type_babele.configure(state="disabled")
        self.radio_input_type_localization.configure(state="disabled")
        self.module_name_entry.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.mock_switch.configure(state="disabled")


    # ===========================================
    # Function: Enable Configuration Controls
    #
    # ===========================================
    def enable_configuration_controls(self):

        self.file_button.configure(state="normal")
        self.radio_input_type_babele.configure(state="normal")
        self.radio_input_type_localization.configure(state="normal")
        self.module_name_entry.configure(state="normal")
        self.start_button.configure(state="normal")
        self.mock_switch.configure(state="normal")


    # ===========================================
    # Function: Initialize Visual Process Status
    # Visualizes the last state of an existing, resumable process
    # ===========================================
    def init_visual_process_status(self):
        self.LOGGER("init_visual_process_status # TODO - not implemented")
        pass # TODO - not implemented


    # ===========================================
    # Function: Submit YES
    # Used by the "Yes" button
    # ===========================================
    def submit_yes(self):

        if "response_queue" in self.current_request:
            self.current_request["response_queue"].put(config.YES)

        elif "on_yes" in self.current_request:
            self.current_request["on_yes"]()


    # ===========================================
    # Function: Submit NO
    # Used by the "No" button
    # ===========================================
    def submit_no(self):

        if "response_queue" in self.current_request:
            self.current_request["response_queue"].put(config.NO)

        elif "on_no" in self.current_request:
            self.current_request["on_no"]()


    # ===========================================
    # Function: Cancel
    # Used by the "Cancel" button
    # ===========================================
    def cancel(self):
        self.cancel_event.set()
        self.cancel_button.configure(text="Please wait ...",
                                     state="disabled")  # This one's needed for interrupting running API calls
        self.current_request["response_queue"].put(config.CANCEL)  # ... this one for interrupting user prompts


    # ===========================================
    # Function: Hide All Prompts
    #
    # ===========================================
    def hide_all_prompts(self):
        self.question_label.pack_forget()
        self.text_answer_entry.pack_forget()
        self.buttons_frame.pack_forget()
        self.submit_button.pack_forget()
        self.yes_button.pack_forget()
        self.no_button.pack_forget()


    # ===========================================
    # Function: Show Buttons Frame
    #
    # ===========================================
    def show_buttons_frame(self):
        self.buttons_frame.pack(
            padx=20,
            pady=5
        )


    # ===========================================
    # Function: Show Cancel Button
    #
    # ===========================================
    def show_cancel_button(self):
        self.cancel_button.pack(side="right", padx=5)


    # ===========================================
    # Function: Hide Cancel Button
    #
    # ===========================================
    def hide_cancel_button(self):
        self.cancel_button.pack_forget()


    # ===========================================
    # Function: Show Question Label
    #
    # ===========================================
    def show_question_label(self):
        self.question_label.pack(padx=20, pady=(10, 5), anchor="w")


    # ===========================================
    # Function: Show Text Answer Entry
    #
    # ===========================================
    def show_text_answer_entry(self):
        self.text_answer_entry.pack(padx=20, pady=5, fill="x")


    # ===========================================
    # Function: Show Submit Button
    #
    # ===========================================
    def show_submit_button(self):
        self.submit_button.pack(side="left", padx=5)


    # ===========================================
    # Function: Show Yes/No Buttons
    #
    # ===========================================
    def show_yesno_buttons(self):
        self.yes_button.pack(side="left", padx=5)
        self.no_button.pack(side="left", padx=5)


    # ===========================================
    # Function: Worker Exception Handler
    # Responsible for catching any error occurring within the asynchronous translation thread
    # Primarily useful for intercepting when user has pressed CANCEL
    # ===========================================
    def worker_exception_handler(self, args):

        msg = f"An Exception occurred:\n{args}"
        self.LOGGER(msg, config.TAG_ERROR)
        if self.LOGGER != print:
            print(msg)
        # self.LOGGER("Cancelled.", config.TAG_ERROR)

        self.cancel_button.configure(text="Cancel", state="enabled")
        self.hide_all_prompts()
        self.enable_configuration_controls()


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


# Finally, run it!
app = App()
fn.set_logger(app.LOGGER)

fn.init_system_dirs()

app.worker_exception_handler = app.worker_exception_handler
threading.excepthook = app.worker_exception_handler

app.mainloop()

import queue
import dialogs
import threading
import translate
import config
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Foundry VTT Translator")

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
            text="No file selected"
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
            text="Module name (overwrite as needed)"
        )

        self.module_name_label.pack(padx=20, pady=(20, 0))

        self.module_name_entry = ctk.CTkEntry(
            self,
            width=300
        )

        self.module_name_entry.pack(padx=20, pady=5, fill="x")

        self.module_name_entry.insert(0, "(Please pick a file first)")


        # =========================================
        # Start Button
        # =========================================
        self.start_button = ctk.CTkButton(
            self,
            text="Start Translation",
            command=self.start_translation
        )

        self.start_button.pack(padx=20, pady=20)

        self.start_button.configure(state="disabled")


        # =========================================
        # Log Output Window
        # =========================================
        self.log = ctk.CTkTextbox(self, width=600, height=300)

        self.log.pack(padx=20, pady=20, fill="both", expand=True)

        # Initialize Logger
        self.LOGGER = self.log_message


        # =========================================
        # Dynamic prompts (initially hidden)
        # =========================================
        self.current_response_queue = None

        self.current_radio_buttons = []

        self.question_label = ctk.CTkLabel(
            self,
            text=""
        )
        self.question_label.pack(padx=20, pady=(10, 5), anchor="w")

        self.answer_entry = ctk.CTkEntry(
            self,
            width=400
        )
        self.answer_entry.pack(padx=20, pady=5, fill="x")

        self.submit_button = ctk.CTkButton(
            self,
            text="OK",
            command=self.process_dialog_response
        )
        self.submit_button.pack(padx=20, pady=(0, 20))

        # Set them all initially to invisible
        self.question_label.pack_forget()
        self.answer_entry.pack_forget()
        self.submit_button.pack_forget()


        # =========================================
        # Now go for it!
        # =========================================
        self.process_dialog_requests()



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
            text=self.selected_file.name
        )

        suggested_module_name = dialogs.suggest_module_name(
            config.INPUT_FILE,
            self.input_type_var.get()
        )

        self.module_name_entry.delete(0, "end")
        self.module_name_entry.insert(0, suggested_module_name)

        self.start_button.configure(state="enabled")


    # ===========================================
    # Function: Start Translation
    # Runs the main worker thread (translation) asynchronously
    # ===========================================
    def start_translation(self):

        if config.INPUT_FILE is None:
            self.log_message("Please select an input file first.")
            return

        config.INPUT_TYPE = self.input_type_var.get()
        config.MODULE_NAME = self.module_name_entry.get().strip()

        self.start_button.configure(state="disabled")

        threading.Thread(
            target=translate.run_translation,
            kwargs={
                # deine normalen Parameter ...
                "logger": self.log_message,
                "finished": self.translation_finished,
            },
            daemon=True
        ).start()


    # ===========================================
    # Function: Translation Finished
    # A callback invoked when start_translation() completes
    # Its main function is to reactivate the start button
    # ===========================================
    def translation_finished(self):
        self.after(
            0,
            lambda: self.start_button.configure(state="normal")
        )


    # ===========================================
    # Function: Process Dialog Requests
    # Processes dialog requests from the translation engine and dynamically
    # displays the corresponding UI elements in the main application window.
    # ===========================================
    def process_dialog_requests(self):

        try:
            request = dialogs.get_request()

        except queue.Empty:
            pass

        else:
            if request["type"] == "radio":
                self.current_response_queue = request["response_queue"]

                self.question_label.configure(
                    text=request["question"]
                )

                self.question_label.pack(
                    padx=20,
                    pady=(10, 5),
                    anchor="w"
                )

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

                self.submit_button.pack(
                    padx=20,
                    pady=(10, 20)
                )

            elif request["type"] == "text":
                self.current_response_queue = request["response_queue"]

                self.question_label.configure(
                    text=request["question"]
                )

                self.question_label.pack(
                    padx=20,
                    pady=(10, 5),
                    anchor="w"
                )

                self.answer_entry.pack(
                    padx=20,
                    pady=5,
                    fill="x"
                )

                self.submit_button.pack(
                    padx=20,
                    pady=(10, 20)
                )

                self.answer_entry.focus()

            else:
                print("UNBEKANNTER REQUEST")

        self.after(50, self.process_dialog_requests)


    # ===========================================
    # Function: Log Message
    # Writes the message passed to the configured logger
    # ===========================================
    def log_message(self, message):
        self.log.insert("end", message + "\n")
        self.log.see("end")


    # ===========================================
    # Function: Process Dialog Response
    # Submits the current dialog response, delivers it to the waiting request,
    # and removes any temporary dialog controls from the UI.
    # ===========================================
    def process_dialog_response(self):

        if self.current_response_queue is None:
            return

        if self.current_radio_buttons:
            answer = self.radio_var.get()

        else:
            answer = self.answer_entry.get().strip().upper()

        self.current_response_queue.put(answer)

        self.answer_entry.delete(0, "end")

        self.question_label.pack_forget()
        self.answer_entry.pack_forget()
        self.submit_button.pack_forget()

        self.current_response_queue = None

        for radio in self.current_radio_buttons:
            radio.destroy()

        self.current_radio_buttons.clear()


# Finally, run it!
app = App()
app.mainloop()
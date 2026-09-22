import ct4f_config as config
import ct4f_translator_dialogs as dialogs
import customtkinter as ctk
import ct4f_security as security


LOGGER = print

# ===========================================
# Function: Set Logger
# Receives the shared logger from the main workflow
# If not invoked, logger will be the simple "print"
# ===========================================
def set_logger(logger):
    global LOGGER
    LOGGER = logger


# ===========================================
# Function: Confirm Yes/No
#
# ===========================================
def confirm_yes_no(question, on_yes, on_no):

    LOGGER(f"confirm_yes_no: \"{question}\"")

    dialogs.put_request({
        "type": config.PROMPT_TYPE_YESNO,
        "question": question,
        "on_yes": on_yes,
        "on_no": on_no
    })


# ------------------------------------------------------------
# Function: Suggest Module Name
# Try to extract module name from input filename
# If not successful, return config.UNKNOWN_MODULE_NAME
# ------------------------------------------------------------
def suggest_module_name(input_file, input_type):
    suggested = config.UNKNOWN_MODULE_NAME

    if input_type == config.INPUT_TYPE_BABELE:
        if input_file.name.count(".") > 1:
            suggested = input_file.name[0: input_file.name.find('.')]

        return suggested

    elif input_type == config.INPUT_TYPE_LOCALIZATION:

        current = input_file.parent

        while True:

            folder_name = current.name.lower()

            if folder_name == config.INPUT_FOLDER_NAME.lower():
                return config.UNKNOWN_MODULE_NAME

            if folder_name not in {
                "lang",
                "language",
                "languages"
            }:
                return current.name

            current = current.parent

    return suggested


class SettingsDialog(ctk.CTkToplevel):

    def __init__(self, parent, on_save_callback=None):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("550x210")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_save_callback = on_save_callback

        # Input field
        ctk.CTkLabel(self, text="API Key:", font=("Arial", 14, "bold")).pack(
            padx=20, pady=(15, 5), anchor="w"
        )
        self.entry = ctk.CTkEntry(self, width=500, show="•")
        self.entry.pack(padx=20, pady=5)

        # Load existing key
        current_key = security.get_api_key()
        if current_key:
            self.entry.insert(0, current_key)

        # Toggle visibility
        self.show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="Show key",
            variable=self.show_var,
            command=self._toggle_show,
        ).pack(padx=20, pady=5, anchor="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(
            side="right", padx=(5, 0)
        )
        ctk.CTkButton(
            btn_frame, text="Cancel", fg_color="gray", command=self.destroy
        ).pack(side="right")

    def _toggle_show(self):
        self.entry.configure(show="" if self.show_var.get() else "•")

    def _save(self):
        security.set_api_key(self.entry.get().strip())
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()


class ErrorDialog(ctk.CTkToplevel):

    def __init__(self, parent, message:str=""):
        super().__init__(parent)
        self.title("Ooops... we have a problem!")
        self.geometry("500x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # =========================================
        # Error Message Window
        # =========================================
        self.err_window = ctk.CTkTextbox(self, width=300, height=300, fg_color="black", text_color="white")
        self.err_window.tag_config(config.TAG_ERROR, foreground="red")
        self.err_window.pack(padx=20, pady=20, fill="both", expand=False)
        self.err_window.insert("end", message, config.TAG_ERROR)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(
            btn_frame, text="Close", fg_color="gray", command=self.destroy
        ).pack(side="right")


class HintDialog(ctk.CTkToplevel):

    def __init__(self, parent, message: str = ""):
        super().__init__(parent)
        self.title("Please note")
        self.minsize(400, 150)
        self.transient(parent)
        self.grab_set()

        # Message (wrapped)
        ctk.CTkLabel(
            self,
            text=message,
            wraplength=400,
            justify="left",
            font=("Arial", 14)
        ).pack(padx=20, pady=(20, 10), fill="both", expand=True)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(btn_frame, text="OK", command=self.destroy).pack(side="right")


class ConfirmDialog(ctk.CTkToplevel):

    def __init__(self, parent, question: str, on_yes, on_no):
        super().__init__(parent)
        self.title("Please confirm")
        self.minsize(400, 150)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: self._answer(on_no))

        # Message (wrapped)
        ctk.CTkLabel(
            self,
            text=question,
            wraplength=400,
            justify="left",
            font=("Arial", 14)
        ).pack(padx=20, pady=(20, 10), fill="both", expand=True)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(btn_frame, text="Yes", command=lambda: self._answer(on_yes)).pack(side="right", padx=(5, 0))
        ctk.CTkButton(btn_frame, text="No", fg_color="gray", command=lambda: self._answer(on_no)).pack(side="right")

    def _answer(self, callback):
        self.destroy()
        if callback:
            callback()

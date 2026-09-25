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
            btn_frame, text="Cancel", fg_color=config.GREY, command=self.destroy
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
        self.err_window = ctk.CTkTextbox(
            self, width=300, height=300,
            fg_color=config.LOG_BACKGROUND_COLOR, text_color=config.LOG_TEXT_COLOR, font=config.LOG_FONT
        )
        self.err_window.tag_config(config.TAG_ERROR, foreground=config.LOG_TAG_COLORS[config.TAG_ERROR])
        self.err_window.pack(padx=20, pady=20, fill="both", expand=False)
        self.err_window.insert("end", message, config.TAG_ERROR)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(
            btn_frame, text="Close", fg_color=config.GREY, command=self.destroy
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

    def __init__(self, parent, question: str, on_yes, on_no, get_log_text=None):
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
        ctk.CTkButton(btn_frame, text="Yes", command=lambda: self._answer(on_yes)).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="No", fg_color=config.GREY, command=lambda: self._answer(on_no)).pack(side="left")

        if get_log_text:
            ctk.CTkButton(
                btn_frame,
                text="Show Log",
                fg_color=config.GREY,
                command=lambda: LogViewerDialog(self, get_log_text())
            ).pack(side="left", padx=(20, 0))

    def _answer(self, callback):
        self.destroy()
        if callback:
            callback()


class LogViewerDialog(ctk.CTkToplevel):

    def __init__(self, parent, log_text: str):
        super().__init__(parent)
        self.title("Log")
        self.geometry("800x600")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # Log content (read-only, scrollable)
        self.log_view = ctk.CTkTextbox(
            self, fg_color=config.LOG_BACKGROUND_COLOR, text_color=config.LOG_TEXT_COLOR, font=config.LOG_FONT
        )
        self.log_view.pack(padx=20, pady=20, fill="both", expand=True)
        self.log_view.insert("end", log_text)
        self.log_view.see("end")
        self.log_view.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 15), fill="x")
        ctk.CTkButton(btn_frame, text="Close", fg_color=config.GREY, command=self.destroy).pack(side="right")


class ReviewItemsDialog(ctk.CTkToplevel):

    def __init__(self, parent, review_items: list):
        super().__init__(parent)
        self.title(f"Review Items ({len(review_items)})")
        self.geometry("900x700")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # Review items content (read-only, scrollable)
        self.view = ctk.CTkTextbox(
            self, fg_color=config.LOG_BACKGROUND_COLOR, text_color=config.LOG_TEXT_COLOR,
            font=config.LOG_FONT, wrap="word"
        )
        self.view.pack(padx=20, pady=20, fill="both", expand=True)
        self.view.tag_config("header", foreground=config.MAGENTA)
        self.view.tag_config("label", foreground="gray70")
        self.view.tag_config("placeholder", foreground=config.BLACK, background=config.YELLOW)

        for position, item in enumerate(review_items, start=1):
            self._render_item(position, item)

        self.view.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 15), fill="x")
        ctk.CTkButton(btn_frame, text="Close", fg_color=config.GREY, command=self.destroy).pack(side="right")


    def _render_item(self, position, item):
        details = item["details"]
        placeholder = details["placeholder"]

        self.view.insert(
            "end",
            f"#{position}  {placeholder}  =  {details['original_value']}   "
            f"(found {details['count']}x in the translation)\n",
            "header"
        )

        self.view.insert("end", "Original:\n", "label")
        self._insert_with_highlight(details["original_context"], placeholder)

        self.view.insert("end", "\n\nTranslation:\n", "label")
        self._insert_with_highlight(details["translated_context"], placeholder)

        self.view.insert("end", "\n\n" + "-" * 80 + "\n\n")

    def _insert_with_highlight(self, text, placeholder):
        parts = text.split(placeholder)

        for index, part in enumerate(parts):
            self.view.insert("end", part)
            if index < len(parts) - 1:
                self.view.insert("end", placeholder, "placeholder")

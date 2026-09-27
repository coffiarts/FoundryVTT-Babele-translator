import ct4f_config as config
import ct4f_settings as settings
import ct4f_i18n as i18n
import ct4f_security as security
import ct4f_core_functions as fn
import ct4f_translator_dialogs as dialogs
import ct4f_ui_widgets as ui_widgets
import customtkinter as ctk
from tkinter import TclError

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
def confirm_yes_no(key, on_yes, on_no, **params):

    LOGGER(f"confirm_yes_no: \"{i18n.t_en(key, **params)}\"")

    dialogs.put_request({
        "type": config.PROMPT_TYPE_YESNO,
        "question": i18n.t(key, **params),
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
        self.title(i18n.t("settings.title"))
        self.geometry("550x670")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_save_callback = on_save_callback

        self.locked_look = ui_widgets.LockedLook()

        # UI language: one entry per language file found in the lang folder
        self.language_by_option = {
            f"{code}: {name}": code for code, name in i18n.available_languages().items()
        }
        self.ui_language_var = ctk.StringVar(value=next(
            (option for option, code in self.language_by_option.items() if code == config.UI_LANGUAGE),
            next(iter(self.language_by_option))
        ))

        ctk.CTkLabel(self, text=i18n.t("settings.ui_language"), font=(config.FONT_FAMILY_LOG, 14, "bold")).pack(
            padx=20, pady=(15, 5), anchor="w"
        )
        ctk.CTkOptionMenu(
            self, width=300, dynamic_resizing=False,
            values=list(self.language_by_option), variable=self.ui_language_var
        ).pack(padx=20, pady=5, anchor="w")

        # UI theme: Radio buttons, each rendered in its own theme's font (a live preview)
        self.ui_theme_var = ctk.StringVar(value=config.UI_THEME)

        ctk.CTkLabel(self, text=i18n.t("settings.ui_theme"), font=(config.FONT_FAMILY_LOG, 14, "bold")).pack(
            padx=20, pady=(15, 5), anchor="w"
        )
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.pack(padx=20, pady=5, anchor="w")
        ctk.CTkRadioButton(
            theme_frame, text=i18n.t("settings.theme_fantasy"), value="fantasy", variable=self.ui_theme_var,
            font=(config.THEME_FONT_FAMILIES["fantasy"], 16, "bold")
        ).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(
            theme_frame, text=i18n.t("settings.theme_neutral"), value="neutral", variable=self.ui_theme_var,
            font=(config.THEME_FONT_FAMILIES["neutral"], 16, "bold")
        ).pack(side="left")
        ctk.CTkRadioButton(
            theme_frame, text=i18n.t("settings.theme_scifi"), value="scifi", variable=self.ui_theme_var,
            font=(config.THEME_FONT_FAMILIES["scifi"], 16, "bold")
        ).pack(side="left")

        # LLM model
        ctk.CTkLabel(self, text=i18n.t("settings.llm_model"), font=(config.FONT_FAMILY_LOG, 14, "bold")).pack(
            padx=20, pady=(15, 5), anchor="w"
        )
        self.model_entry = ctk.CTkEntry(self, width=500)
        self.model_entry.pack(padx=20, pady=5)
        self.model_entry.insert(0, config.LLM_MODEL)

        # API base URL (empty = OpenAI)
        ctk.CTkLabel(self, text=i18n.t("settings.api_base_url"), font=(config.FONT_FAMILY_LOG, 14, "bold")).pack(
            padx=20, pady=(15, 5), anchor="w"
        )
        self.base_url_entry = ctk.CTkEntry(self, width=500)
        self.base_url_entry.pack(padx=20, pady=0)
        self.base_url_entry.insert(0, config.API_BASE_URL)
        ctk.CTkLabel(
            self,
            text=i18n.t("settings.default_url", url=config.OPENAI_BASE_URL),
            text_color=config.INK,
            font=(config.FONT_FAMILY_LOG, 12),
        ).pack(padx=30, pady=(0, 0), anchor="w")

        # API key
        ctk.CTkLabel(self, text=i18n.t("settings.api_key"), font=(config.FONT_FAMILY_LOG, 14, "bold")).pack(
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
        self.show_key_checkbox = ctk.CTkCheckBox(
            self,
            text=i18n.t("settings.show_key"),
            variable=self.show_var,
            command=self._toggle_show,
        )
        self.show_key_checkbox.pack(padx=20, pady=5, anchor="w")

        # Only relevant for servers other than OpenAI, which always needs a key
        self.no_key_var = ctk.BooleanVar(value=not config.API_KEY_REQUIRED)
        self.no_key_checkbox = ctk.CTkCheckBox(
            self,
            text=i18n.t("settings.no_key_needed"),
            variable=self.no_key_var,
            command=self._update_key_controls,
        )
        self.no_key_checkbox.pack(padx=20, pady=(15, 0), anchor="w")
        ctk.CTkLabel(
            self,
            text=i18n.t("settings.no_key_hint"),
            text_color=config.INK,
            font=(config.FONT_FAMILY_LOG, 12),
        ).pack(padx=48, pady=(0, 5), anchor="w")

        self._update_key_controls()

        # LLM connection settings must not change while a run is active, since they take effect immediately
        if parent.is_busy:
            for widget in (self.model_entry, self.base_url_entry, self.entry, self.show_key_checkbox, self.no_key_checkbox):
                widget.configure(state="disabled")
                self.locked_look.apply(widget, True)

        # Hide tooltips option
        self.hide_tooltips_var = ctk.BooleanVar(value=config.HIDE_TOOLTIPS)
        ctk.CTkCheckBox(
            self,
            text=i18n.t("settings.hide_tooltips"),
            variable=self.hide_tooltips_var,
        ).pack(padx=20, pady=(20, 5), anchor="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(btn_frame, text=i18n.t("dialog.save"), command=self._save).pack(
            side="right", padx=(5, 0)
        )
        ctk.CTkButton(
            btn_frame, text=i18n.t("dialog.cancel"), fg_color=config.GREY, command=self.destroy
        ).pack(side="right")

        ui_widgets.center_over_parent(self, parent)

    def _toggle_show(self):
        self.entry.configure(show="" if self.show_var.get() else "•")

    def _update_key_controls(self):
        locked = self.no_key_var.get()
        state = "disabled" if locked else "normal"

        self.entry.configure(state=state)
        self.show_key_checkbox.configure(state=state)

        self.locked_look.apply(self.entry, locked)
        self.locked_look.apply(self.show_key_checkbox, locked)

    def _save(self):
        # An empty model field keeps the current model
        config.LLM_MODEL = self.model_entry.get().strip() or config.LLM_MODEL
        config.API_BASE_URL = self.base_url_entry.get().strip() or config.OPENAI_BASE_URL

        config.API_KEY_REQUIRED = not self.no_key_var.get()
        config.HIDE_TOOLTIPS = self.hide_tooltips_var.get()

        settings.update_settings({
            "llm_model": config.LLM_MODEL,
            "api_base_url": config.API_BASE_URL,
            "api_key_required": config.API_KEY_REQUIRED,
            "hide_tooltips": config.HIDE_TOOLTIPS
        })

        security.set_api_key(self.entry.get().strip())

        # A changed UI language or theme only takes effect after a restart
        new_language = self.language_by_option[self.ui_language_var.get()]
        language_changed = new_language != config.UI_LANGUAGE
        theme_changed = self.ui_theme_var.get() != config.UI_THEME

        if language_changed:
            settings.update_settings({"ui_language": new_language})

        if theme_changed:
            settings.update_settings({"ui_theme": self.ui_theme_var.get()})

        config.UI_LANGUAGE = new_language
        config.UI_THEME = self.ui_theme_var.get()

        if self.on_save_callback:
            self.on_save_callback()

        parent = self.master
        self.destroy()

        if language_changed or theme_changed:
            if parent.is_busy:
                HintDialog(parent, message=i18n.t("settings.restart_busy"))
            else:
                ConfirmDialog(
                    parent,
                    question=i18n.t("settings.restart_prompt"),
                    on_yes=fn.restart_app,
                    on_no=None
                )


class ErrorDialog(ctk.CTkToplevel):

    def __init__(self, parent, message:str=""):
        super().__init__(parent)
        self.title(i18n.t("dialog.error_title"))
        self.geometry("500x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # =========================================
        # Error Message Window
        # =========================================
        self.err_window = ctk.CTkTextbox(
            self, width=300, height=300,
            fg_color=config.LOG_BACKGROUND_COLOR, text_color=config.LOG_TEXT_COLOR, font=config.FONT_LOG
        )
        self.err_window.tag_config(config.TAG_ERROR, foreground=config.LOG_TAG_COLORS[config.TAG_ERROR])
        self.err_window.pack(padx=20, pady=20, fill="both", expand=False)
        self.err_window.insert("end", message, config.TAG_ERROR)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(
            btn_frame, text=i18n.t("dialog.close"), fg_color=config.GREY, command=self.destroy
        ).pack(side="right")

        ui_widgets.center_over_parent(self, parent)


class HintDialog(ctk.CTkToplevel):

    def __init__(self, parent, message: str = ""):
        super().__init__(parent)
        self.title(i18n.t("dialog.hint_title"))
        self.minsize(400, 150)
        self.transient(parent)
        self.grab_set()

        # Message (wrapped)
        ctk.CTkLabel(
            self,
            text=message,
            wraplength=400,
            justify="left",
            font=(config.FONT_FAMILY_LOG, 14)
        ).pack(padx=20, pady=(20, 10), fill="both", expand=True)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(btn_frame, text=i18n.t("dialog.ok"), command=self.destroy).pack(side="right")

        ui_widgets.center_over_parent(self, parent)


class ConfirmDialog(ctk.CTkToplevel):

    def __init__(self, parent, question: str, on_yes, on_no, on_show_log=None):
        super().__init__(parent)
        self.title(i18n.t("dialog.confirm_title"))
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
            font=(config.FONT_FAMILY_LOG, 14)
        ).pack(padx=20, pady=(20, 10), fill="both", expand=True)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(10, 15), fill="x")
        ctk.CTkButton(btn_frame, text=i18n.t("dialog.yes"), command=lambda: self._answer(on_yes)).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame, text=i18n.t("dialog.no"), fg_color=config.GREY, command=lambda: self._answer(on_no)).pack(side="left")

        if on_show_log:
            ctk.CTkButton(
                btn_frame,
                text=i18n.t("dialog.show_log"),
                fg_color=config.GREY,
                command=on_show_log
            ).pack(side="left", padx=(20, 0))

        ui_widgets.center_over_parent(self, parent)


    def _answer(self, callback):
        self.destroy()
        if callback:
            callback()


# ===========================================
# Class: Log Viewer Dialog
# Permanent pop-out log: created hidden at startup,
# receives every log line, shown on demand.
# ===========================================
class LogViewerDialog(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title(i18n.t("dialog.log_title"))
        self.geometry("800x600")
        self.resizable(True, True)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.hide)

        # Log content (read-only, scrollable)
        self.log_view = ui_widgets.LogTextbox(self)
        self.log_view.pack(padx=20, pady=20, fill="both", expand=True)
        self.log_view.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 15), fill="x")
        ctk.CTkButton(btn_frame, text=i18n.t("dialog.close"), fg_color=config.GREY, command=self.hide).pack(side="right")

        self._was_maximized = False
        self._normal_geometry = None

        self.withdraw()

    def append(self, message, tag=""):
        self.log_view.append(message, tag)

    def show(self, modal=False):
        if self._normal_geometry:
            self.geometry(self._normal_geometry)
        else:
            ui_widgets.center_over_parent(self, self.master)

        self.deiconify()

    def hide(self):
        state = self.state()

        if state == "normal":
            self._normal_geometry = self.geometry()

        if state != "withdrawn":
            self._was_maximized = (state == "zoomed")

        self.grab_release()
        self.withdraw()


class ReviewItemsDialog(ctk.CTkToplevel):

    def __init__(self, parent, review_items: list):
        super().__init__(parent)
        self.title(i18n.t("review.title", count=len(review_items)))
        self.geometry("900x700")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # Review items content (read-only, scrollable)
        self.view = ctk.CTkTextbox(
            self, fg_color=config.LOG_BACKGROUND_COLOR, text_color=config.LOG_TEXT_COLOR,
            font=config.FONT_LOG, wrap="word"
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
        ctk.CTkButton(btn_frame, text=i18n.t("dialog.close"), fg_color=config.GREY, command=self.destroy).pack(side="right")

        ui_widgets.center_over_parent(self, parent)


    def _render_item(self, position, item):
        details = item["details"]
        placeholder = details["placeholder"]

        self.view.insert(
            "end",
            i18n.t("review.item_header", position=position, placeholder=placeholder,
                   value=details['original_value'], count=details['count']) + "\n",
            "header"
        )

        self.view.insert("end", i18n.t("review.original") + "\n", "label")
        self._insert_with_highlight(details["original_context"], placeholder)

        self.view.insert("end", "\n\n" + i18n.t("review.translation") + "\n", "label")
        self._insert_with_highlight(details["translated_context"], placeholder)

        self.view.insert("end", "\n\n" + "-" * 80 + "\n\n")

    def _insert_with_highlight(self, text, placeholder):
        parts = text.split(placeholder)

        for index, part in enumerate(parts):
            self.view.insert("end", part)
            if index < len(parts) - 1:
                self.view.insert("end", placeholder, "placeholder")

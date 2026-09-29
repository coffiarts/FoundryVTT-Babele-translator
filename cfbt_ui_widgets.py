import cfbt_config as config
import cfbt_i18n as i18n
import customtkinter as ctk
import tkinter as tk
from collections.abc import Callable

ICON_SIZE = 22  # px, size of one batch square
ICON_GAP = 4    # px, gap between squares

# CTk doesn't recolor disabled widgets by itself: widget type => theme_extras color KEY to apply
# while locked. The color itself is looked up lazily in LockedLook.apply(), not stored here directly,
# since this module is imported before the active theme's colors are resolved
LOCKED_COLORS = {
    ctk.CTkButton: {"fg_color": "INK_LOCKED"},
    ctk.CTkOptionMenu: {"fg_color": "INK_LOCKED", "button_color": "INK_LOCKED"},
    ctk.CTkRadioButton: {"fg_color": "INK_LOCKED", "border_color": "INK_LOCKED"},
    ctk.CTkCheckBox: {"fg_color": "INK_LOCKED", "border_color": "INK_LOCKED"},
    ctk.CTkEntry: {"border_color": "INK_LOCKED", "text_color": "INK_LOCKED"},
    ctk.CTkSlider: {"progress_color": "INK_LOCKED", "button_color": "INK_LOCKED"},
    ctk.CTkSwitch: {"progress_color": "INK_LOCKED", "button_color": "INK_LOCKED"},
    ctk.CTkFrame: {"fg_color": "PARCHMENT_LOCKED"},
    ctk.CTkLabel: {"text_color": "INK_LOCKED"}
}


# ===========================================
# Class: Locked Look
# Gives disabled widgets a clearly "locked" appearance and restores their original
# colors afterwards. One instance remembers the original colors of the widgets it handled
# ===========================================
class LockedLook:

    def __init__(self):
        self._original_colors = {}

    def apply(self, widget, locked):

        locked_keys = LOCKED_COLORS[type(widget)]
        locked_colors = {prop: config.theme_extras["colors"][key] for prop, key in locked_keys.items()}

        if locked:
            # Locking twice must not overwrite the remembered original colors
            if widget not in self._original_colors:
                self._original_colors[widget] = {key: widget.cget(key) for key in locked_colors}
                widget.configure(**locked_colors)

        elif widget in self._original_colors:
            widget.configure(**self._original_colors.pop(widget))


# ===========================================
# Class: Batch Status Bar
# Renders one square per batch (wrapped onto several rows if needed),
# a "x / y completed" caption and a Clear button.
# Data input is a list of dicts, one per batch, like:
#   {"batch_id": 12, "status": config.COMPLETED, "char_count": 48987, ...}
# ===========================================
class BatchStatusBar(ctk.CTkFrame):

    def __init__(self, parent, title, on_clear=None):
        super().__init__(parent, fg_color="transparent")

        self.batches = []
        self.icons = []
        self._columns = 0

        # Header: title (left) + Clear button (right)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x")

        self.title_label = ctk.CTkLabel(self.header, text=title, font=config.FONT_HEADING)
        self.title_label.pack(side="left")

        self.clear_button = ctk.CTkButton(self.header, text=i18n.t("button.clear"), width=70, command=on_clear)
        self.clear_button.pack(side="right")
        self._clear_default_color = self.clear_button.cget("fg_color")

        # Icon area: the squares are re-gridded whenever the available width changes
        self.icon_area = ctk.CTkFrame(self, fg_color="transparent")
        self.icon_area.pack(fill="x", pady=(5, 0))
        self.icon_area.bind("<Configure>", lambda event: self._layout_icons())

        self.caption_label = ctk.CTkLabel(self, text="", anchor="w")
        self.caption_label.pack(fill="x")

        self.set_batches([])


    # ===========================================
    # Function: Set Batches
    # Single entry point for rendering (initial, resume and live updates)
    # ===========================================
    def set_batches(self, batches):
        self.batches = list(batches)

        # Only recreate the squares if the number of batches changed, otherwise just recolor them
        if len(self.icons) != len(self.batches):
            for icon in self.icons:
                icon.destroy()

            self.icons = [
                ctk.CTkFrame(self.icon_area, width=ICON_SIZE, height=ICON_SIZE, corner_radius=3)
                for _ in self.batches
            ]
            self._columns = 0  # force a fresh layout
            self._layout_icons()

        for icon, batch in zip(self.icons, self.batches):
            icon.configure(fg_color=config.STATUS_COLORS[batch["status"]])

        # REVIEW_REQUIRED counts as completed (the user has already accepted the batch)
        completed = sum(
            1 for batch in self.batches
            if batch["status"] in (config.COMPLETED, config.REVIEW_REQUIRED)
        )
        self.caption_label.configure(text=i18n.t("stats.batch_progress", completed=completed, total=len(self.batches)))


    # ===========================================
    # Function: Layout Icons
    # Distributes the squares across as many rows as the current width requires
    # ===========================================
    def _layout_icons(self):
        columns = max(1, self.icon_area.winfo_width() // (ICON_SIZE + ICON_GAP))

        if columns == self._columns:
            return
        self._columns = columns

        for index, icon in enumerate(self.icons):
            icon.grid(
                row=index // columns,
                column=index % columns,
                padx=(0, ICON_GAP),
                pady=(0, ICON_GAP)
            )

    # ===========================================
    # Function: Set Clear Enabled
    # Locks/unlocks the Clear button (e.g. while a process is running)
    # ===========================================
    def set_clear_enabled(self, enabled):
        self.clear_button.configure(
            state="normal" if enabled else "disabled",
            fg_color=self._clear_default_color if enabled else config.theme_extras["colors"]["INK_LOCKED"]
        )


# ===========================================
# Class: Log Text Box
# Text box for log output.
# Tags are colored according to config.LOG_TAG_COLORS.
# ===========================================
class LogTextbox(ctk.CTkTextbox):

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=config.LOG_BACKGROUND_COLOR,
            text_color=config.LOG_TEXT_COLOR,
            font=config.FONT_LOG,
            **kwargs
        )

        for tag, color in config.LOG_TAG_COLORS.items():
            self.tag_config(tag, foreground=color)

    def append(self, message, tag=""):
        # Works for read-only (disabled) boxes as well
        state = self.cget("state")
        self.configure(state="normal")
        self.insert("end", message + "\n", tag)
        self.see("end")
        self.configure(state=state)


# ===========================================
# Class: Tooltip
# Hover info for a widget: a small borderless popup that appears after a short delay.
# <text> is a string, or a function returning one (for texts that change, e.g. truncated paths)
# ===========================================
class Tooltip:

    DELAY_MS = 500
    MAX_WIDTH = 360  # px, longer texts are wrapped

    def __init__(self, widget, text):
        self.widget = widget
        self.text: Callable|str = text
        self._after_id = None
        self._popup = None
        self._pointer = (0, 0)

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Motion>", self._remember_pointer, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _remember_pointer(self, event):
        self._pointer = (event.x_root, event.y_root)

    def _schedule(self, event):
        self._hide()
        self._remember_pointer(event)
        self._after_id = self.widget.after(self.DELAY_MS, self._show)

    def _show(self):
        self._after_id = None
        text = self.text() if callable(self.text) else self.text

        if config.HIDE_TOOLTIPS or not text:
            return

        self._popup = tk.Toplevel(self.widget)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_attributes("-topmost", True)

        tk.Label(
            self._popup,
            text=text,
            justify="left",
            wraplength=self.MAX_WIDTH,
            background=config.theme_extras["colors"]["PARCHMENT_LIGHT"],
            foreground=config.theme_extras["colors"]["INK_CONTRAST"],
            relief="solid",
            borderwidth=1,
            font=config.FONT_TOOLTIP,
            padx=8,
            pady=4
        ).pack()

        # Keep the popup on screen: flip to the left of / above the pointer if there is no room
        self._popup.update_idletasks()
        width, height = self._popup.winfo_reqwidth(), self._popup.winfo_reqheight()
        x, y = self._pointer[0] + 12, self._pointer[1] + 18

        if x + width > self.widget.winfo_screenwidth():
            x = max(0, self._pointer[0] - width - 12)

        if y + height > self.widget.winfo_screenheight():
            y = max(0, self._pointer[1] - height - 12)

        self._popup.wm_geometry(f"+{x}+{y}")

    def _hide(self, event=None):
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

        if self._popup is not None:
            self._popup.destroy()
            self._popup = None


# ------------------------------------------------------------
# Function: Center Over Parent
# Positions <dialog> centered over <parent> (same screen as the app, not the top-left corner
# Tk defaults new Toplevels to), clamped so it doesn't end up partially off-screen
# ------------------------------------------------------------
def center_over_parent(dialog, parent):
    dialog.update_idletasks()

    width = dialog.winfo_width()
    height = dialog.winfo_height()

    x = parent.winfo_x() + (parent.winfo_width() - width) // 2
    y = parent.winfo_y() + (parent.winfo_height() - height) // 2

    dialog.geometry(f"+{x}+{y}")

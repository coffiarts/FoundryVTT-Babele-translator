import ct4f_config as config
import customtkinter as ctk

ICON_SIZE = 22  # px, size of one batch square
ICON_GAP = 4    # px, gap between squares


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

        self.title_label = ctk.CTkLabel(self.header, text=title, font=("Arial", 16, "bold"))
        self.title_label.pack(side="left")

        self.clear_button = ctk.CTkButton(self.header, text="Clear", width=70, command=on_clear)
        self.clear_button.pack(side="right")

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
        self.caption_label.configure(text=f"{completed} / {len(self.batches)} completed")


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
        self.clear_button.configure(state="normal" if enabled else "disabled")


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
            font=config.LOG_FONT,
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

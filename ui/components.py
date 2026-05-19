import tkinter as tk
import tkinter.font as tkfont

from ui.theme import COLORS, FONT, tone_color, tone_soft


class AppButton(tk.Canvas):
    def __init__(self, parent, text, command, variant="primary", **kwargs):
        self._text = text
        self._command = command
        self._variant = variant
        self._state = kwargs.pop("state", "normal")
        self._char_width = kwargs.pop("width", None)
        self._font = kwargs.pop("font", (FONT, 10, "bold"))
        self._padx = kwargs.pop("padx", 18)
        self._pady = kwargs.pop("pady", 10)
        canvas_bg = kwargs.pop("bg", parent.cget("bg"))
        super().__init__(
            parent,
            bg=canvas_bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
            cursor="hand2" if self._state == "normal" else "arrow",
            **kwargs,
        )
        self._hover = False
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._redraw()

    def _palette(self, variant):
        if variant == "secondary":
            return COLORS["surface"], COLORS["primary"], COLORS["border_strong"], COLORS["surface_alt"]
        if variant == "success":
            return COLORS["success"], COLORS["surface"], COLORS["success"], COLORS["primary"]
        if variant == "danger":
            return COLORS["danger"], COLORS["surface"], COLORS["danger"], "#b91c1c"
        if variant == "ghost":
            return COLORS["surface"], COLORS["text"], COLORS["border"], COLORS["surface_soft"]
        return COLORS["primary"], COLORS["surface"], COLORS["primary"], COLORS["border_strong"]

    def _on_click(self, _event):
        if self._state == "normal" and callable(self._command):
            self._command()

    def _on_enter(self, _event):
        if self._state == "normal":
            self._hover = True
            self._redraw()

    def _on_leave(self, _event):
        self._hover = False
        self._redraw()

    def _measure_width(self):
        font = tkfont.Font(font=self._font)
        text_width = font.measure(self._text)
        width = text_width + self._padx * 2 + 16
        if self._char_width is not None:
            width = max(width, int(self._char_width) * 11 + self._padx * 2)
        return width

    def _redraw(self):
        fill, fg, outline, hover_fill = self._palette(self._variant)
        if self._state != "normal":
            fill = COLORS["surface_soft"]
            fg = COLORS["muted_soft"]
            outline = COLORS["border"]
            hover_fill = fill
        elif self._hover:
            fill = hover_fill

        width = self._measure_width()
        height = 44
        super().configure(width=width, height=height)
        self.delete("all")
        self._draw_pill(3, 3, width - 3, height - 3, 20, fill, outline, 2)
        self.create_text(
            width / 2,
            height / 2,
            text=self._text,
            fill=fg,
            font=self._font,
        )

    def _draw_pill(self, x1, y1, x2, y2, radius, fill, outline, line_width):
        points = [
            x1 + radius, y1,
            x1 + radius, y1,
            x2 - radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1 + radius,
            x1, y1,
        ]
        self.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=outline,
            width=line_width,
        )

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        redraw = False
        cursor = None
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            redraw = True
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            cursor = "hand2" if self._state == "normal" else "arrow"
            redraw = True
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "width" in kwargs:
            self._char_width = kwargs.pop("width")
            redraw = True
        if "font" in kwargs:
            self._font = kwargs.pop("font")
            redraw = True
        if cursor is not None:
            kwargs["cursor"] = cursor
        super().configure(**kwargs)
        if redraw:
            self._redraw()

    config = configure


class Badge(tk.Frame):
    def __init__(self, parent, text, tone="primary", **kwargs):
        super().__init__(parent, bg=tone_soft(tone), **kwargs)
        tk.Label(
            self,
            text=text,
            bg=tone_soft(tone),
            fg=tone_color(tone),
            font=(FONT, 9, "bold"),
            padx=10,
            pady=4,
        ).pack()


class SectionHeader(tk.Frame):
    def __init__(self, parent, title, subtitle="", action=None, **kwargs):
        super().__init__(parent, bg=COLORS["app_bg"], **kwargs)
        left = tk.Frame(self, bg=COLORS["app_bg"])
        left.pack(side="left", fill="x", expand=True)
        tk.Label(
            left,
            text=title,
            bg=COLORS["app_bg"],
            fg=COLORS["text"],
            font=(FONT, 15, "bold"),
        ).pack(anchor="w")
        if subtitle:
            tk.Label(
                left,
                text=subtitle,
                bg=COLORS["app_bg"],
                fg=COLORS["muted"],
                font=(FONT, 9),
            ).pack(anchor="w", pady=(2, 0))
        if action is not None:
            action.pack(side="right")


class StepChip(tk.Frame):
    def __init__(self, parent, index, label, active=False, **kwargs):
        bg = COLORS["primary_soft"] if active else COLORS["surface"]
        fg = COLORS["primary"] if active else COLORS["muted"]
        super().__init__(parent, bg=bg, highlightthickness=1, highlightbackground=COLORS["border"], **kwargs)
        tk.Label(
            self,
            text=f"{index}. {label}",
            bg=bg,
            fg=fg,
            font=(FONT, 9, "bold"),
            padx=10,
            pady=6,
        ).pack()


class StatusPill(tk.Frame):
    def __init__(self, parent, text="Ready", tone="muted", **kwargs):
        super().__init__(parent, bg=tone_soft(tone), **kwargs)
        self._label = tk.Label(
            self,
            text=text,
            bg=tone_soft(tone),
            fg=tone_color(tone),
            font=(FONT, 9, "bold"),
            padx=12,
            pady=5,
        )
        self._label.pack()
        self._tone = tone

    def set(self, text, tone="muted"):
        self.configure(bg=tone_soft(tone))
        self._label.configure(text=text, bg=tone_soft(tone), fg=tone_color(tone))
        self._tone = tone

import tkinter as tk

COLORS = {
    "app_bg": "#ffffff",
    "surface": "#ffffff",
    "surface_alt": "#eef7ff",
    "surface_soft": "#f7fbff",
    "border": "#b5d8f3",
    "border_strong": "#5ba8e6",
    "primary": "#0e84d8",
    "primary_soft": "#ddeffd",
    "success": "#0b95c9",
    "success_soft": "#def5fd",
    "warning": "#2c76cf",
    "warning_soft": "#e8f1fe",
    "danger": "#dc2626",
    "danger_soft": "#fee2e2",
    "text": "#0e84d8",
    "muted": "#5f95c5",
    "muted_soft": "#b9cee2",
    "wave_bg": "#edf7ff",
}

FONT = "Arial"
MONO = "Arial"


def tone_color(tone: str) -> str:
    return {
        "primary": COLORS["primary"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "danger": COLORS["danger"],
        "muted": COLORS["muted"],
    }.get(tone, COLORS["text"])


def tone_soft(tone: str) -> str:
    return {
        "primary": COLORS["primary_soft"],
        "success": COLORS["success_soft"],
        "warning": COLORS["warning_soft"],
        "danger": COLORS["danger_soft"],
        "muted": COLORS["surface_soft"],
    }.get(tone, COLORS["surface_soft"])


def blend_color(color: str, background: str, alpha: float) -> str:
    r1, g1, b1 = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    r2, g2, b2 = int(background[1:3], 16), int(background[3:5], 16), int(background[5:7], 16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 * alpha + r2 * (1 - alpha)),
        int(g1 * alpha + g2 * (1 - alpha)),
        int(b1 * alpha + b2 * (1 - alpha)),
    )


def make_card(parent, padding=18, bg=None, border=None):
    card = tk.Frame(
        parent,
        bg=bg or COLORS["surface"],
        highlightthickness=1,
        highlightbackground=border or COLORS["border"],
        bd=0,
    )
    inner = tk.Frame(card, bg=bg or COLORS["surface"])
    inner.pack(fill="both", expand=True, padx=padding, pady=padding)
    return card, inner

"""
Panel 1 — Landing Page
Shows: title, tagline, badge pills, Start button, pulsing shield
"""

import tkinter as tk

C = {
    "bg":    "#0b0f1a",
    "card":  "#161d2e",
    "green": "#00ff88",
    "green_dim": "#00c060",
    "blue":  "#38bdf8",
    "yellow":"#fbbf24",
    "purple":"#8b5cf6",
    "text":  "#e2e8f0",
    "muted": "#64748b",
}
F = "Courier New"


class LandingPanel(tk.Frame):
    def __init__(self, parent, on_start_clicked, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._on_start = on_start_clicked
        self._pulse_r   = 30
        self._pulse_grow = True
        self._build()

    def _build(self):
        # Full height hero
        hero = tk.Frame(self, bg=C["bg"], height=400)
        hero.pack(fill="x")
        hero.pack_propagate(False)

        # Pulse canvas — shield animation
        self.pulse_cv = tk.Canvas(
            hero, width=130, height=130,
            bg=C["bg"], highlightthickness=0
        )
        self.pulse_cv.place(relx=0.5, rely=0.20, anchor="center")

        # Draw shield shape using canvas polygons (works on all platforms)
        self.pulse_cv.create_polygon(
            65, 18,   # top centre
            95, 30,   # top right
            95, 60,   # mid right
            65, 90,   # bottom point
            35, 60,   # mid left
            35, 30,   # top left
            fill="",
            outline=C["green"], width=3, tags="icon"
        )
        self.pulse_cv.create_polygon(
            65, 28,
            88, 38,
            88, 60,
            65, 82,
            42, 60,
            42, 38,
            fill="#0b1a10", outline="", tags="icon"
        )
        # Inner check mark
        self.pulse_cv.create_line(
            52, 56, 62, 68, 80, 44,
            fill=C["green"], width=3, tags="icon"
        )
        self._tick_pulse()

        # Main title
        tk.Label(
            hero,
            text="BULLY SPEECH DETECTION",
            bg=C["bg"], fg=C["green"],
            font=(F, 28, "bold"),
        ).place(relx=0.5, rely=0.50, anchor="center")

        # Subtitle
        tk.Label(
            hero,
            text="Real-time voice monitoring  ·  AI-powered detection  ·  Instant alerts",
            bg=C["bg"], fg=C["muted"],
            font=(F, 10),
        ).place(relx=0.5, rely=0.62, anchor="center")

        # Badge pills
        badges = tk.Frame(hero, bg=C["bg"])
        badges.place(relx=0.5, rely=0.76, anchor="center")

        for txt, col in [
            ("🎙 Whisper ASR",     C["blue"]),
            ("🤖 Toxic-BERT",      C["purple"]),
            ("📱 Telegram Alerts", C["yellow"]),
            ("🔒 100% Offline",    C["green"]),
        ]:
            pill = tk.Frame(badges, bg=C["card"],
                            highlightthickness=1,
                            highlightbackground=col)
            pill.pack(side="left", padx=6)
            tk.Label(pill, text=txt, bg=C["card"], fg=col,
                     font=(F, 8, "bold"), padx=12, pady=5).pack()

        # Start button
        tk.Button(
            hero,
            text="▶   START DETECTION SYSTEM",
            bg=C["green"], fg=C["bg"],
            font=(F, 11, "bold"),
            relief="flat", padx=30, pady=11,
            activebackground=C["green_dim"],
            activeforeground=C["bg"],
            cursor="hand2",
            command=self._on_start,
        ).place(relx=0.5, rely=0.90, anchor="center")

    def _tick_pulse(self):
        c = self.pulse_cv
        c.delete("pulse")
        r = self._pulse_r

        # Outer glow ring
        c.create_oval(65-r-6, 65-r-6, 65+r+6, 65+r+6,
                      outline=self._fade(C["green"], 0.15),
                      width=1, tags="pulse")
        # Main pulse ring
        alpha = 0.6 - (self._pulse_r - 28) / 44.0
        c.create_oval(65-r, 65-r, 65+r, 65+r,
                      outline=self._fade(C["green"], max(0.1, alpha)),
                      width=2, tags="pulse")
        # Always keep shield on top
        c.tag_raise("icon")

        if self._pulse_grow:
            self._pulse_r += 1
            if self._pulse_r >= 52: self._pulse_grow = False
        else:
            self._pulse_r -= 1
            if self._pulse_r <= 26: self._pulse_grow = True

        self.after(35, self._tick_pulse)

    def _fade(self, hex_col, alpha):
        r,g,b = int(hex_col[1:3],16), int(hex_col[3:5],16), int(hex_col[5:7],16)
        bg_r, bg_g, bg_b = 0x0b, 0x0f, 0x1a
        return "#{:02x}{:02x}{:02x}".format(
            int(r*alpha + bg_r*(1-alpha)),
            int(g*alpha + bg_g*(1-alpha)),
            int(b*alpha + bg_b*(1-alpha)),
        )

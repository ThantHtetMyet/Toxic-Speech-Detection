"""
Panel 2 — Microphone Scanner
Shows: radar animation + scan button
"""

import tkinter as tk
import math

C = {
    "bg":     "#0b0f1a",
    "card":   "#161d2e",
    "border": "#1e2d45",
    "green":  "#00ff88",
    "yellow": "#fbbf24",
    "text":   "#e2e8f0",
    "muted":  "#64748b",
}
F = "Courier New"


class ScanPanel(tk.Frame):
    def __init__(self, parent, on_scan_clicked, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._on_scan    = on_scan_clicked
        self._angle      = 0
        self._running    = False
        self._build()
        self._tick()

    def _build(self):
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=80, pady=40)

        # Section header
        _sec_hdr(body, "02", "MICROPHONE SCAN")

        content = tk.Frame(body, bg=C["bg"])
        content.pack(fill="x", pady=12)

        # ── Radar ──
        left = tk.Frame(content, bg=C["bg"])
        left.pack(side="left", padx=(0, 50))

        self.radar = tk.Canvas(left, width=220, height=220,
                               bg=C["bg"], highlightthickness=0)
        self.radar.pack()
        self._draw_base()

        # ── Controls ──
        right = tk.Frame(content, bg=C["bg"])
        right.pack(side="left", fill="x", expand=True)

        tk.Label(right,
                 text="Scan your system for available audio input devices.",
                 bg=C["bg"], fg=C["text"],
                 font=(F, 11)).pack(anchor="w", pady=(10, 6))

        tk.Label(right,
                 text="All microphones connected to this computer\nwill be listed in the panel below.",
                 bg=C["bg"], fg=C["muted"],
                 font=(F, 9), justify="left").pack(anchor="w", pady=(0, 16))

        self.btn = tk.Button(
            right,
            text="⬤   SCAN MICROPHONES",
            bg=C["card"], fg=C["green"],
            font=(F, 10, "bold"),
            relief="solid", bd=1,
            highlightthickness=1,
            highlightbackground=C["green"],
            padx=22, pady=10,
            activebackground=C["border"],
            activeforeground=C["green"],
            cursor="hand2",
            command=self._clicked,
        )
        self.btn.pack(anchor="w")

        self.status = tk.Label(
            right, text="",
            bg=C["bg"], fg=C["muted"],
            font=(F, 8)
        )
        self.status.pack(anchor="w", pady=(8, 0))

    def _clicked(self):
        self.btn.config(state="disabled", text="⬤   SCANNING…")
        self.status.config(text="Scanning for audio devices…", fg=C["yellow"])
        self._running = True
        self.radar.delete("blip")
        self._on_scan()

    def scan_done(self, count):
        self._running = False
        self.btn.config(state="normal", text="⬤   SCAN MICROPHONES")
        self.status.config(
            text=f"✓  Found {count} microphone(s)  —  click TARGET on a device below",
            fg=C["green"]
        )

    def add_blip(self, idx, total, name):
        c = self.radar; cx = cy = 110
        a = (idx / max(total,1)) * 2 * math.pi - math.pi/2
        r = 28 + (idx % 3) * 26
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        c.create_oval(x-5, y-5, x+5, y+5,
                      fill=C["green"], outline="", tags="blip")
        c.create_text(x+7, y, text=name[:10], fill=C["green"],
                      font=(F, 6), anchor="w", tags="blip")

    def _draw_base(self):
        c = self.radar; cx = cy = 110
        for r in [100, 72, 44, 18]:
            c.create_oval(cx-r, cy-r, cx+r, cy+r,
                          outline=C["border"], width=1)
        c.create_line(cx, cy-100, cx, cy+100, fill=C["border"])
        c.create_line(cx-100, cy, cx+100, cy, fill=C["border"])
        c.create_oval(cx-4, cy-4, cx+4, cy+4,
                      fill=C["green"], outline="")

    def _tick(self):
        if self._running:
            c = self.radar; cx = cy = 110
            c.delete("sweep")
            a = math.radians(self._angle)
            for i, alpha in enumerate([0.55, 0.28, 0.10]):
                off = math.radians(self._angle - i*10)
                xe  = cx + 100*math.sin(off)
                ye  = cy - 100*math.cos(off)
                col = _blend(C["green"], C["bg"], alpha)
                c.create_line(cx, cy, xe, ye,
                              fill=col, width=max(1,3-i), tags="sweep")
            xe = cx + 100*math.sin(a)
            ye = cy - 100*math.cos(a)
            c.create_line(cx, cy, xe, ye,
                          fill=C["green"], width=2, tags="sweep")
            self._angle = (self._angle + 4) % 360
        self.after(30, self._tick)


def _sec_hdr(parent, num, title):
    f = tk.Frame(parent, bg=C["bg"])
    f.pack(fill="x", pady=(0, 4))
    tk.Label(f, text=num, bg=C["bg"], fg=C["green"],
             font=(F, 22, "bold")).pack(side="left", padx=(0,12))
    vf = tk.Frame(f, bg=C["bg"])
    vf.pack(side="left")
    tk.Label(vf, text=title, bg=C["bg"], fg=C["text"],
             font=(F, 12, "bold")).pack(anchor="w")
    tk.Frame(f, bg=C["border"], height=1).pack(
        side="left", fill="x", expand=True, padx=(16,0), pady=10)

def _blend(c1, c2, a):
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1*a+r2*(1-a)), int(g1*a+g2*(1-a)), int(b1*a+b2*(1-a)))

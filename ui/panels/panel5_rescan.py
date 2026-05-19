"""
Panel 5 — Rescan Footer
Shows: rescan button + instructions
"""

import tkinter as tk

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


class RescanPanel(tk.Frame):
    def __init__(self, parent, on_rescan, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._on_rescan = on_rescan
        self._build()

    def _build(self):
        wrap = tk.Frame(self, bg=C["bg"])
        wrap.pack(fill="both", expand=True, padx=80, pady=60)

        _sec_hdr(wrap, "05", "RESCAN")

        body = tk.Frame(wrap, bg=C["bg"])
        body.pack(fill="x", pady=10)

        info = tk.Frame(body, bg=C["bg"])
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info,
                 text="Need to detect new microphones?",
                 bg=C["bg"], fg=C["text"],
                 font=(F, 10, "bold")).pack(anchor="w")

        tk.Label(info,
                 text="Click RESCAN DEVICES to refresh the microphone list.\n"
                      "New devices will appear in section 03.",
                 bg=C["bg"], fg=C["muted"],
                 font=(F, 8), justify="left").pack(anchor="w", pady=(4,0))

        tk.Button(
            body,
            text="↺   RESCAN DEVICES",
            bg=C["card"], fg=C["yellow"],
            font=(F, 9, "bold"),
            relief="solid", bd=1,
            highlightthickness=1,
            highlightbackground=C["yellow"],
            padx=20, pady=10,
            activebackground=C["border"],
            activeforeground=C["yellow"],
            cursor="hand2",
            command=self._on_rescan,
        ).pack(side="right")

        # Footer line
        tk.Frame(wrap, bg=C["border"], height=1).pack(fill="x", pady=(20,4))

        tk.Label(
            wrap,
            text="BullyDetector POC  ·  Whisper ASR + Toxic-BERT  ·  All processing done locally  ·  No internet required",
            bg=C["bg"], fg=C["muted"],
            font=(F, 7)
        ).pack(pady=(0,10))


def _sec_hdr(parent, num, title):
    f = tk.Frame(parent, bg=C["bg"])
    f.pack(fill="x", pady=(0,4))
    tk.Label(f, text=num, bg=C["bg"], fg=C["green"],
             font=(F, 22, "bold")).pack(side="left", padx=(0,12))
    vf = tk.Frame(f, bg=C["bg"])
    vf.pack(side="left")
    tk.Label(vf, text=title, bg=C["bg"], fg=C["text"],
             font=(F, 12, "bold")).pack(anchor="w")
    tk.Frame(f, bg=C["border"], height=1).pack(
        side="left", fill="x", expand=True, padx=(16,0), pady=10)

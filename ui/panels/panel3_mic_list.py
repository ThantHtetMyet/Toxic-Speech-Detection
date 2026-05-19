"""
Panel 3 — Detected Microphones List
Shows: grid of mic cards with name, ID, rate, TARGET button
"""

import tkinter as tk

C = {
    "bg":       "#0b0f1a",
    "card":     "#161d2e",
    "card2":    "#1a2235",
    "border":   "#1e2d45",
    "green":    "#00ff88",
    "green_dim":"#00c060",
    "blue":     "#38bdf8",
    "text":     "#e2e8f0",
    "muted":    "#64748b",
}
F = "Courier New"


class MicListPanel(tk.Frame):
    def __init__(self, parent, on_target_clicked, on_refresh=None, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._on_target  = on_target_clicked
        self._on_refresh = on_refresh or (lambda: None)
        self._targeted_ids = set()
        self._build()

    def set_refresh_callback(self, cb):
        self._on_refresh = cb

    def _build(self):
        wrap = tk.Frame(self, bg=C["bg"])
        wrap.pack(fill="both", expand=True, padx=60, pady=30)

        _sec_hdr(wrap, "03", "DETECTED MICROPHONES")

        # Top bar — info + refresh button
        top_bar = tk.Frame(wrap, bg=C["bg"])
        top_bar.pack(fill="x", pady=(4, 0))

        tk.Label(top_bar,
                 text="Click  + TARGET  on any microphone to add it to the detection panel  (max 3)",
                 bg=C["bg"], fg=C["muted"],
                 font=(F, 8)).pack(side="left", anchor="w")

        self.refresh_btn = tk.Button(
            top_bar,
            text="↺  REFRESH LIST",
            bg=C["card"], fg=C["green"],
            font=(F, 7, "bold"),
            relief="solid", bd=1,
            highlightbackground=C["green"],
            padx=12, pady=4,
            cursor="hand2",
            activebackground=C["border"],
            command=self._on_refresh_clicked
        )
        self.refresh_btn.pack(side="right")

        # Hint for webcam
        tk.Label(wrap,
                 text="💡 If your webcam mic isn't showing — plug it in first, then click REFRESH LIST",
                 bg=C["bg"], fg=C["muted"],
                 font=(F, 7)).pack(anchor="w", pady=(2, 8))

        # Scrollable canvas for mic grid
        canvas_wrap = tk.Frame(wrap, bg=C["bg"])
        canvas_wrap.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(canvas_wrap, bg=C["bg"],
                                 highlightthickness=0)
        vsb = tk.Scrollbar(canvas_wrap, orient="vertical",
                           command=self._canvas.yview,
                           bg=C["border"], troughcolor=C["bg"])
        self._canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.grid_frame = tk.Frame(self._canvas, bg=C["bg"])
        self._canvas_win = self._canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw"
        )

        self.grid_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Empty state
        self.empty_lbl = tk.Label(
            self.grid_frame,
            text="No microphones detected yet.\nRun SCAN MICROPHONES in section 02 above.",
            bg=C["bg"], fg=C["muted"],
            font=(F, 9), justify="center"
        )
        self.empty_lbl.pack(pady=30)

    def _on_frame_configure(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._canvas_win, width=e.width)

    def _on_mousewheel(self, e):
        self._canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    def _on_refresh_clicked(self):
        self.refresh_btn.config(state="disabled", text="↺  Scanning…")
        self.after(200, lambda: self.refresh_btn.config(
            state="normal", text="↺  REFRESH LIST"))
        self._on_refresh()

    def render(self, devices: list, targeted_ids: set):
        """Re-render the mic card grid."""
        self._targeted_ids = targeted_ids

        for w in self.grid_frame.winfo_children():
            w.destroy()

        if not devices:
            tk.Label(self.grid_frame,
                     text="No microphones found. Try rescanning.",
                     bg=C["bg"], fg=C["muted"],
                     font=(F, 9)).pack(pady=30)
            return

        COLS = 3
        row_frame = None

        for i, dev in enumerate(devices):
            col_idx = i % COLS

            if col_idx == 0:
                row_frame = tk.Frame(self.grid_frame, bg=C["bg"])
                row_frame.pack(fill="x", pady=5)

            self._make_card(row_frame, dev)

    def _make_card(self, parent, dev):
        already = dev["id"] in self._targeted_ids

        card = tk.Frame(
            parent,
            bg=C["card"],
            highlightthickness=2,
            highlightbackground=C["green_dim"] if already else C["border"],
            width=300, height=130
        )
        card.pack(side="left", padx=6, expand=True, fill="x")
        card.pack_propagate(False)

        # Top row — icon + name
        top = tk.Frame(card, bg=C["card"])
        top.pack(fill="x", padx=14, pady=(12, 4))

        tk.Label(top, text="🎙",
                 bg=C["card"],
                 font=("Segoe UI Emoji", 22)).pack(side="left", padx=(0,10))

        info = tk.Frame(top, bg=C["card"])
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info,
                 text=dev["name"][:30],
                 bg=C["card"], fg=C["text"],
                 font=(F, 8, "bold"),
                 wraplength=200,
                 justify="left").pack(anchor="w")

        tk.Label(info,
                 text=f"Device ID: {dev['id']}",
                 bg=C["card"], fg=C["muted"],
                 font=(F, 7)).pack(anchor="w")

        # Specs row
        specs = tk.Frame(card, bg=C["card"])
        specs.pack(fill="x", padx=14, pady=(0,8))

        for txt, col in [
            (f"{dev['rate']} Hz",      C["blue"]),
            (f"{dev['channels']} ch",  C["muted"]),
        ]:
            pill = tk.Frame(specs, bg=C["card2"],
                            highlightthickness=1,
                            highlightbackground=C["border"])
            pill.pack(side="left", padx=(0,4))
            tk.Label(pill, text=txt, bg=C["card2"], fg=col,
                     font=(F, 7), padx=6, pady=2).pack()

        # TARGET button
        btn_txt = "✓  TARGETED" if already else "+  TARGET"
        btn_fg  = C["green_dim"] if already else C["green"]

        tk.Button(
            card,
            text=btn_txt,
            bg=C["card"], fg=btn_fg,
            font=(F, 7, "bold"),
            relief="solid", bd=1,
            highlightbackground=btn_fg,
            padx=12, pady=4,
            cursor="hand2" if not already else "arrow",
            state="disabled" if already else "normal",
            activebackground=C["border"],
            activeforeground=C["green"],
            command=lambda d=dev: self._on_target(d),
        ).pack(anchor="e", padx=14, pady=(0,10))


def _sec_hdr(parent, num, title):
    f = tk.Frame(parent, bg=C["bg"])
    f.pack(fill="x", pady=(0,4))
    tk.Label(f, text=num, bg=C["bg"], fg=C["green"],
             font=(F, 22, "bold")).pack(side="left", padx=(0,12))
    vf = tk.Frame(f, bg=C["bg"])
    vf.pack(side="left")
    tk.Label(vf, text=title, bg=C["bg"], fg=C["text"],
             font=(F, 12, "bold")).pack(anchor="w")
    tk.Frame(f, bg="#1e2d45", height=1).pack(
        side="left", fill="x", expand=True, padx=(16,0), pady=10)
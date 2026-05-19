"""
Panel 4 — Main Detection Panel
No-flicker design: mic cards are never destroyed while running.
Cards update in-place instead of being rebuilt.
"""

import tkinter as tk
import time
import os

C = {
    "bg":       "#0b0f1a",
    "panel":    "#111827",
    "card":     "#161d2e",
    "card2":    "#1a2235",
    "border":   "#1e2d45",
    "green":    "#00ff88",
    "green_dim":"#00c460",
    "red":      "#ff3b3b",
    "red_dim":  "#cc1010",
    "yellow":   "#fbbf24",
    "blue":     "#38bdf8",
    "text":     "#e2e8f0",
    "muted":    "#64748b",
    "wave":     "#0d1526",
}
F  = "Courier New"
FE = "Segoe UI Emoji"
MAX_MICS = 3


class MicCard(tk.Frame):
    """Single mic monitoring card — updates in-place, never rebuilt."""

    def __init__(self, parent, mic, is_running,
                 on_start, on_stop, on_remove, **kwargs):
        super().__init__(parent, bg=C["card"],
                         highlightthickness=2,
                         highlightbackground=C["green"] if is_running else C["border"],
                         **kwargs)
        self.mic        = mic
        self.is_running = is_running
        self._on_start  = on_start
        self._on_stop   = on_stop
        self._on_remove = on_remove

        self.wave_levels    = [0.0] * 60
        self._pulse_r       = 8.0
        self._pulse_grow    = True
        self._timer_running = False
        self._timer_start   = 0.0
        self._timer_timeout = 0
        self._timer_label   = ""

        self._build()
        self._tick_wave()
        self._tick_pulse()

    def _build(self):
        mid  = self.mic["id"]
        name = self.mic["name"]

        # Header
        hdr = tk.Frame(self, bg=C["card2"])
        hdr.pack(fill="x")

        left_hdr = tk.Frame(hdr, bg=C["card2"])
        left_hdr.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        self.pulse_cv = tk.Canvas(left_hdr, width=16, height=16,
                                  bg=C["card2"], highlightthickness=0)
        self.pulse_cv.pack(side="left", padx=(0,6))

        tk.Label(left_hdr, text=name[:22],
                 bg=C["card2"], fg=C["green"] if self.is_running else C["text"],
                 font=(F, 8, "bold")).pack(side="left")

        self.btn_remove = tk.Button(
            hdr, text="✕", bg=C["card2"], fg=C["muted"],
            font=(F, 8), relief="flat", padx=6, pady=4,
            cursor="hand2", activebackground=C["border"],
            state="disabled" if self.is_running else "normal",
            command=lambda: self._on_remove(mid)
        )
        self.btn_remove.pack(side="right", padx=4)

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # Waveform
        tk.Label(self, text="LIVE WAVEFORM",
                 bg=C["card"], fg=C["muted"],
                 font=(F, 6, "bold")).pack(anchor="w", padx=8, pady=(6,2))

        self.wave_cv = tk.Canvas(self, height=52, bg=C["wave"],
                                 highlightthickness=1,
                                 highlightbackground=C["border"])
        self.wave_cv.pack(fill="x", padx=8)

        # Status box
        self.status_frame = tk.Frame(self, bg=C["card"],
                                     highlightthickness=1,
                                     highlightbackground=C["border"])
        self.status_frame.pack(fill="x", padx=8, pady=(6,2))

        self.status_lbl = tk.Label(
            self.status_frame,
            text="🟡 MONITORING" if self.is_running else "⚫ IDLE",
            bg=C["card"],
            fg=C["yellow"] if self.is_running else C["muted"],
            font=(F, 9, "bold"), pady=4
        )
        self.status_lbl.pack(fill="x")

        # Progress bar
        self.prog_bg = tk.Frame(self, bg=C["border"], height=5)
        self.prog_bg.pack(fill="x", padx=8, pady=(2,0))
        self.prog_fg = tk.Frame(self.prog_bg, bg=C["green"], height=5, width=0)
        self.prog_fg.place(x=0, y=0)

        # Timer
        self.timer_lbl = tk.Label(self, text="",
                                  bg=C["card"], fg=C["muted"], font=(F, 7))
        self.timer_lbl.pack(anchor="w", padx=8, pady=(2,2))

        # Buttons
        bf = tk.Frame(self, bg=C["card"])
        bf.pack(fill="x", padx=8, pady=(4,10))

        self.btn_start = tk.Button(
            bf, text="▶  START",
            bg=C["card"] if self.is_running else C["green"],
            fg=C["muted"] if self.is_running else C["bg"],
            font=(F, 7, "bold"), relief="flat",
            padx=10, pady=5, cursor="hand2",
            state="disabled" if self.is_running else "normal",
            activebackground=C["green_dim"],
            command=lambda: self._on_start(self.mic)
        )
        self.btn_start.pack(side="left", padx=(0,4))

        self.btn_stop = tk.Button(
            bf, text="■  STOP",
            bg=C["red"] if self.is_running else C["card"],
            fg="white"   if self.is_running else C["muted"],
            font=(F, 7, "bold"), relief="flat",
            padx=10, pady=5,
            cursor="hand2" if self.is_running else "arrow",
            state="normal" if self.is_running else "disabled",
            activebackground=C["red_dim"],
            command=lambda: self._on_stop(mid)
        )
        self.btn_stop.pack(side="left")

    # ── Update running state IN PLACE (no rebuild) ────────────────────────────
    def set_running(self, running: bool):
        """Called when START/STOP happens — updates buttons without rebuilding."""
        if self.is_running == running:
            return   # no change needed
        self.is_running = running
        mid = self.mic["id"]

        self.configure(highlightbackground=C["green"] if running else C["border"])
        self.btn_remove.config(state="disabled" if running else "normal")
        self.btn_start.config(
            state="disabled" if running else "normal",
            bg=C["card"] if running else C["green"],
            fg=C["muted"] if running else C["bg"],
        )
        self.btn_stop.config(
            state="normal" if running else "disabled",
            bg=C["red"] if running else C["card"],
            fg="white"   if running else C["muted"],
            cursor="hand2" if running else "arrow",
        )
        if not running:
            self.update_status("⚫ STOPPED")
            self.stop_timer()

    # ── Status update ─────────────────────────────────────────────────────────
    def update_status(self, text: str):
        if "Recording" in text or "🎙" in text:
            fg = C["green"]; border = C["green"]; bar_col = C["green"]
        elif "Transcrib" in text or "📝" in text:
            fg = C["blue"];  border = C["blue"];  bar_col = C["blue"]
        elif "Analysing" in text or "🤖" in text:
            fg = C["yellow"]; border = C["yellow"]; bar_col = C["yellow"]
        elif "YES" in text or "Alert" in text or "📱" in text:
            fg = C["red"];   border = C["red"];   bar_col = C["red"]
        elif "Stopped" in text or "⚫" in text or "IDLE" in text:
            fg = C["muted"]; border = C["border"]; bar_col = C["muted"]
            self._set_progress(0, C["muted"])
        else:
            fg = C["muted"]; border = C["border"]; bar_col = C["muted"]

        self.status_lbl.config(text=text, fg=fg)
        self.status_frame.config(highlightbackground=border)

    def _set_progress(self, pct, col):
        self.prog_bg.update_idletasks()
        w = self.prog_bg.winfo_width()
        if w > 2:
            self.prog_fg.config(bg=col, width=max(0, int(w * pct / 100)))
            self.prog_fg.place(x=0, y=0)

    # ── Timer ─────────────────────────────────────────────────────────────────
    def start_timer(self, label, timeout=0):
        self._timer_label   = label
        self._timer_start   = time.time()
        self._timer_timeout = timeout
        self._timer_running = True
        self._tick_timer()

    def stop_timer(self):
        self._timer_running = False
        if self.timer_lbl.winfo_exists():
            self.timer_lbl.config(text="")
        self._set_progress(0, C["muted"])

    def _tick_timer(self):
        if not self.winfo_exists() or not self._timer_running:
            return
        elapsed = time.time() - self._timer_start
        if self._timer_timeout > 0:
            pct = min(100, int(elapsed / self._timer_timeout * 100))
            rem = max(0, self._timer_timeout - elapsed)
            txt = f"{self._timer_label}  {elapsed:.0f}s / {self._timer_timeout}s  ({rem:.0f}s left)"
            col = C["red"] if elapsed > self._timer_timeout * 0.8 else C["yellow"]
            bar = C["green"] if "🎙" in self._timer_label else \
                  C["blue"]  if "📝" in self._timer_label else C["yellow"]
            self._set_progress(pct, bar)
        else:
            txt = f"{self._timer_label}  {elapsed:.1f}s"
            col = C["muted"]
        self.timer_lbl.config(text=txt, fg=col)
        self.after(300, self._tick_timer)

    # ── Audio level ───────────────────────────────────────────────────────────
    def push_level(self, lvl):
        self.wave_levels.pop(0)
        self.wave_levels.append(lvl)

    # ── Waveform animation ────────────────────────────────────────────────────
    def _tick_wave(self):
        if not self.winfo_exists():
            return
        c = self.wave_cv
        c.update_idletasks()
        w = c.winfo_width(); h = c.winfo_height()
        if w > 2 and h > 2:
            c.delete("all")
            mid = h // 2
            bw  = w / len(self.wave_levels)
            col = C["green"] if self.is_running else C["blue"]
            for i, lvl in enumerate(self.wave_levels):
                x   = i * bw
                amp = min(lvl * 400, mid - 2)
                amp = max(amp, 1)
                a   = 0.2 + (i / len(self.wave_levels)) * 0.8
                shade = _blend(col, C["wave"], a)
                c.create_rectangle(x+1, mid-amp, x+bw-1, mid+amp,
                                   fill=shade, outline="")
            c.create_line(0, mid, w, mid, fill=C["border"])
            if self.is_running:
                c.create_oval(w-12, 4, w-4, 12, fill=C["red"], outline="")
        self.after(80, self._tick_wave)

    # ── Pulse dot ─────────────────────────────────────────────────────────────
    def _tick_pulse(self):
        if not self.winfo_exists():
            return
        c = self.pulse_cv
        c.delete("all")
        if self.is_running:
            r = self._pulse_r
            c.create_oval(8-r, 8-r, 8+r, 8+r,
                          outline=_blend(C["green"], C["card2"], 0.3), width=1)
            c.create_oval(4, 4, 12, 12, fill=C["green"], outline="")
            self._pulse_r += 0.4 if self._pulse_grow else -0.4
            if self._pulse_r >= 7:   self._pulse_grow = False
            if self._pulse_r <= 3:   self._pulse_grow = True
        else:
            c.create_oval(5, 5, 11, 11, fill=C["muted"], outline="")
        self.after(60, self._tick_pulse)


class MainPanel(tk.Frame):
    def __init__(self, parent, on_start, on_stop, on_remove, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._on_start  = on_start
        self._on_stop   = on_stop
        self._on_remove = on_remove

        # mic_id → MicCard  (NEVER destroyed while running)
        self.mic_cards: dict[int, MicCard] = {}

        self.total = self.yes_count = self.no_count = 0
        self._empty_result_lbl = None
        self._result_count     = 0

        self._build()

    def _build(self):
        # Section header
        hdr = tk.Frame(self, bg=C["bg"])
        hdr.pack(fill="x", padx=30, pady=(16,8))
        tk.Label(hdr, text="04", bg=C["bg"], fg=C["green"],
                 font=(F, 20, "bold")).pack(side="left", padx=(0,10))
        tk.Label(hdr, text="MAIN DETECTION PANEL",
                 bg=C["bg"], fg=C["text"],
                 font=(F, 12, "bold")).pack(side="left")
        tk.Frame(hdr, bg=C["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(16,0), pady=10)

        # Mic cards row
        mic_sec = tk.Frame(self, bg=C["bg"])
        mic_sec.pack(fill="x", padx=30, pady=(0,6))

        tk.Label(mic_sec,
                 text="TARGETED MICROPHONES — Each shows live recording",
                 bg=C["bg"], fg=C["muted"],
                 font=(F, 7, "bold")).pack(anchor="w", pady=(0,6))

        self.cards_frame = tk.Frame(mic_sec, bg=C["bg"])
        self.cards_frame.pack(fill="x")
        for i in range(MAX_MICS):
            self.cards_frame.columnconfigure(i, weight=1, uniform="mic")

        # Placeholder slots
        self.slots = []
        for i in range(MAX_MICS):
            slot = tk.Frame(self.cards_frame, bg=C["card"],
                            highlightthickness=1,
                            highlightbackground=C["border"],
                            height=200)
            slot.grid(row=0, column=i, padx=4, sticky="nsew")
            slot.grid_propagate(False)
            tk.Label(slot, text=f"SLOT {i+1}\nNo mic targeted",
                     bg=C["card"], fg=C["border"],
                     font=(F, 8), justify="center").pack(expand=True)
            self.slots.append(slot)

        # Stats
        sf = tk.Frame(mic_sec, bg=C["bg"])
        sf.pack(fill="x", pady=(8,0))
        self.lbl_total = tk.Label(sf, text="Clips: 0",
                                  bg=C["bg"], fg=C["muted"], font=(F,7))
        self.lbl_yes   = tk.Label(sf, text="Bullying: 0",
                                  bg=C["bg"], fg=C["red"], font=(F,7,"bold"))
        self.lbl_no    = tk.Label(sf, text="Clean: 0",
                                  bg=C["bg"], fg=C["green"], font=(F,7,"bold"))
        self.lbl_total.pack(side="left", padx=(0,16))
        self.lbl_yes.pack  (side="left", padx=(0,16))
        self.lbl_no.pack   (side="left")

        tk.Frame(self, bg=C["border"], height=1).pack(
            fill="x", padx=30, pady=(8,0))

        # Right panel — log + results
        bot = tk.Frame(self, bg=C["bg"])
        bot.pack(fill="both", expand=True, padx=30, pady=(10,20))
        bot.columnconfigure(0, weight=1)

        # Live log
        tk.Label(bot, text="LIVE ACTIVITY LOG",
                 bg=C["bg"], fg=C["muted"],
                 font=(F, 7, "bold")).pack(anchor="w")

        log_wrap = tk.Frame(bot, bg=C["panel"])
        log_wrap.pack(fill="x", pady=(4,8))

        log_sb = tk.Scrollbar(log_wrap, bg=C["border"],
                              troughcolor=C["bg"], relief="flat")
        log_sb.pack(side="right", fill="y")

        self.live_log = tk.Text(
            log_wrap, bg=C["panel"], fg=C["text"],
            font=(F, 7), relief="flat", height=7,
            wrap="word", state="disabled",
            yscrollcommand=log_sb.set,
        )
        self.live_log.pack(fill="x")
        log_sb.config(command=self.live_log.yview)

        self.live_log.tag_config("yes",    foreground=C["red"],   font=(F,7,"bold"))
        self.live_log.tag_config("no",     foreground=C["green"])
        self.live_log.tag_config("ts",     foreground=C["muted"])
        self.live_log.tag_config("mic",    foreground=C["blue"])
        self.live_log.tag_config("script", foreground="#94a3b8",  font=(F,7,"italic"))

        # Results header
        res_hdr = tk.Frame(bot, bg=C["bg"])
        res_hdr.pack(fill="x", pady=(0,4))
        tk.Label(res_hdr, text="🚨 BULLYING DETECTIONS",
                 bg=C["bg"], fg=C["muted"],
                 font=(F, 7, "bold")).pack(side="left")
        self.res_count_lbl = tk.Label(res_hdr, text="",
                 bg=C["bg"], fg=C["red"], font=(F, 7, "bold"))
        self.res_count_lbl.pack(side="right")

        # Scrollable results area
        res_wrap = tk.Frame(bot, bg=C["bg"])
        res_wrap.pack(fill="both", expand=True)

        res_sb = tk.Scrollbar(res_wrap, bg=C["border"],
                              troughcolor=C["bg"], relief="flat")
        res_sb.pack(side="right", fill="y")

        self.res_canvas = tk.Canvas(res_wrap, bg=C["bg"],
                                    highlightthickness=0,
                                    yscrollcommand=res_sb.set)
        self.res_canvas.pack(side="left", fill="both", expand=True)
        res_sb.config(command=self.res_canvas.yview)

        self.results_frame = tk.Frame(self.res_canvas, bg=C["bg"])
        self._res_win = self.res_canvas.create_window(
            (0,0), window=self.results_frame, anchor="nw")

        self.results_frame.bind("<Configure>",
            lambda e: self.res_canvas.configure(
                scrollregion=self.res_canvas.bbox("all")))
        self.res_canvas.bind("<Configure>",
            lambda e: self.res_canvas.itemconfig(self._res_win, width=e.width))
        self.res_canvas.bind_all("<MouseWheel>",
            lambda e: self.res_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._empty_result_lbl = tk.Label(
            self.results_frame,
            text="🚨 Bullying detections will appear here",
            bg=C["bg"], fg=C["muted"],
            font=(F, 8), justify="center"
        )
        self._empty_result_lbl.pack(pady=30)

    # ── Public: render_targets — NO FLICKER ───────────────────────────────────
    def render_targets(self, targeted: dict, running_ids: set):
        """
        Updates cards in-place. Never destroys a running card.
        Only creates/removes cards for mics that were added/removed.
        """
        current_ids = set(targeted.keys())
        card_ids    = set(self.mic_cards.keys())

        # Remove cards for mics that were un-targeted (only if not running)
        for mid in card_ids - current_ids:
            card = self.mic_cards[mid]
            if not card.is_running:
                card.destroy()
                del self.mic_cards[mid]

        # Update existing cards' running state
        for mid, card in self.mic_cards.items():
            running = mid in running_ids
            card.set_running(running)

        # Create cards for newly targeted mics
        for mid, mic in targeted.items():
            if mid not in self.mic_cards:
                slot_idx = list(targeted.keys()).index(mid)
                if slot_idx >= MAX_MICS:
                    continue
                slot = self.slots[slot_idx]
                # Clear placeholder
                for w in slot.winfo_children():
                    w.destroy()
                running = mid in running_ids
                card = MicCard(
                    slot, mic=mic, is_running=running,
                    on_start  = self._on_start,
                    on_stop   = self._on_stop,
                    on_remove = self._on_remove,
                )
                card.pack(fill="both", expand=True)
                self.mic_cards[mid] = card
                slot.configure(
                    highlightbackground=C["green"] if running else C["border"])

        # Update slot borders
        for i, (mid, mic) in enumerate(targeted.items()):
            if i < MAX_MICS:
                running = mid in running_ids
                self.slots[i].configure(
                    highlightbackground=C["green"] if running else C["border"])

    # ── Public: push level to specific card ──────────────────────────────────
    def push_level(self, mic_id, lvl):
        if mic_id in self.mic_cards:
            self.mic_cards[mic_id].push_level(lvl)

    # ── Public: update status per card ───────────────────────────────────────
    def set_mic_status(self, mic_id, text):
        if mic_id in self.mic_cards:
            self.mic_cards[mic_id].update_status(text)

    def start_mic_timer(self, mic_id, label, timeout=0):
        if mic_id in self.mic_cards:
            self.mic_cards[mic_id].start_timer(label, timeout)

    def stop_mic_timer(self, mic_id):
        if mic_id in self.mic_cards:
            self.mic_cards[mic_id].stop_timer()

    def set_status(self, text):
        pass  # per-card now

    # ── Live log ──────────────────────────────────────────────────────────────
    def log_activity(self, name, result, transcript, scores):
        if not hasattr(self, 'live_log') or not self.live_log.winfo_exists():
            return
        ts  = time.strftime("%H:%M:%S")
        pct = int(scores.get("toxic", 0) * 100)

        self.live_log.config(state="normal")
        self.live_log.insert("end", f"[{ts}] ", "ts")
        self.live_log.insert("end", f"[{name[:14]}] ", "mic")
        self.live_log.insert("end", "🚨 YES  " if result else "✅ NO   ",
                             "yes" if result else "no")
        self.live_log.insert("end", f"toxic={pct}%  ", "ts")
        self.live_log.insert("end",
            f'"{transcript[:55]}{"…" if len(transcript)>55 else ""}"\n', "script")
        self.live_log.see("end")
        self.live_log.config(state="disabled")

    # ── Result cards (YES only) ───────────────────────────────────────────────
    def add_result(self, name, result, transcript, scores, rec_path=None):
        self.total += 1
        if result: self.yes_count += 1
        else:      self.no_count  += 1
        self.lbl_total.config(text=f"Clips: {self.total}")
        self.lbl_yes.config  (text=f"Bullying: {self.yes_count}")
        self.lbl_no.config   (text=f"Clean: {self.no_count}")

        if not result:
            return

        if self._empty_result_lbl and self._empty_result_lbl.winfo_exists():
            self._empty_result_lbl.destroy()
            self._empty_result_lbl = None

        self._result_count += 1
        self.res_count_lbl.config(text=f"{self.yes_count} detected")

        bg = "#160808"

        # Full-width card
        card = tk.Frame(self.results_frame, bg=bg,
                        highlightthickness=2,
                        highlightbackground=C["red"])
        card.pack(fill="x", padx=4, pady=(0,6))

        # ── Card header ───────────────────────────────────────────────────
        hdr_bg = "#220a0a"
        hdr = tk.Frame(card, bg=hdr_bg)
        hdr.pack(fill="x")

        # Left: icon + verdict
        left_hdr = tk.Frame(hdr, bg=hdr_bg)
        left_hdr.pack(side="left", padx=10, pady=6)

        # Pulsing alert indicator
        alert_cv = tk.Canvas(left_hdr, width=14, height=14,
                             bg=hdr_bg, highlightthickness=0)
        alert_cv.pack(side="left", padx=(0,6))
        alert_cv.create_oval(2,2,12,12, fill=C["red"], outline="")

        tk.Label(left_hdr, text="BULLYING DETECTED",
                 bg=hdr_bg, fg=C["red"],
                 font=(F, 10, "bold")).pack(side="left")

        # Right: time + mic
        right_hdr = tk.Frame(hdr, bg=hdr_bg)
        right_hdr.pack(side="right", padx=10, pady=6)

        tk.Label(right_hdr, text=time.strftime("%H:%M:%S"),
                 bg=hdr_bg, fg=C["red"],
                 font=(F, 9, "bold")).pack(anchor="e")
        tk.Label(right_hdr, text=f"🎙 {name[:35]}",
                 bg=hdr_bg, fg=C["muted"],
                 font=(F, 7)).pack(anchor="e")

        tk.Frame(card, bg=C["red"], height=1).pack(fill="x")

        # ── Body: transcript + scores side by side ────────────────────────
        body = tk.Frame(card, bg=bg)
        body.pack(fill="x", padx=10, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)

        # Left: full transcript
        tx_frame = tk.Frame(body, bg=bg)
        tx_frame.grid(row=0, column=0, sticky="nsew", padx=(0,10))

        tk.Label(tx_frame, text="TRANSCRIPT",
                 bg=bg, fg=C["muted"],
                 font=(F, 6, "bold")).pack(anchor="w")

        tx_box = tk.Frame(tx_frame, bg="#1a0a0a",
                          highlightthickness=1,
                          highlightbackground=C["border"])
        tx_box.pack(fill="x", pady=(3,0))

        tk.Label(tx_box,
                 text=f'"{transcript}"',
                 bg="#1a0a0a", fg=C["text"],
                 font=(F, 8), wraplength=500,
                 justify="left",
                 pady=6, padx=8).pack(anchor="w")

        # Right: score bars
        sc_frame = tk.Frame(body, bg=bg)
        sc_frame.grid(row=0, column=1, sticky="nsew")

        tk.Label(sc_frame, text="TOXICITY SCORES",
                 bg=bg, fg=C["muted"],
                 font=(F, 6, "bold")).pack(anchor="w")

        SCORE_LABELS = {
            "toxic":         "Toxic",
            "severe_toxic":  "Severe",
            "obscene":       "Obscene",
            "threat":        "Threat",
            "insult":        "Insult",
            "identity_hate": "Hate",
        }
        for key, label in SCORE_LABELS.items():
            val  = scores.get(key, 0)
            pct  = int(val * 100)
            col  = (C["red"]    if val > 0.5  else
                    C["yellow"] if val > 0.3  else
                    C["muted"])

            row_f = tk.Frame(sc_frame, bg=bg)
            row_f.pack(fill="x", pady=1)

            tk.Label(row_f, text=f"{label:<8}",
                     bg=bg, fg=C["muted"],
                     font=(F, 7), width=8).pack(side="left")

            # Bar background
            bar_bg = tk.Frame(row_f, bg=C["border"], height=8)
            bar_bg.pack(side="left", fill="x", expand=True, padx=(0,4))
            bar_bg.pack_propagate(False)

            # Bar fill
            if pct > 0:
                fill_pct = max(2, pct)
                tk.Frame(bar_bg, bg=col, height=8).place(
                    relx=0, rely=0, relwidth=fill_pct/100, relheight=1)

            tk.Label(row_f, text=f"{pct}%",
                     bg=bg, fg=col,
                     font=(F, 7, "bold"), width=4).pack(side="left")

        # Keep max 20 cards (scrollable so no limit needed)
        cards = list(self.results_frame.winfo_children())
        if len(cards) > 20:
            cards[0].destroy()

        # Scroll to bottom to show latest
        self.res_canvas.after(50,
            lambda: self.res_canvas.yview_moveto(1.0))


def _blend(c1, c2, a):
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1*a+r2*(1-a)), int(g1*a+g2*(1-a)), int(b1*a+b2*(1-a)))
import math
import time
import tkinter as tk

from ui.theme import COLORS, FONT, MONO, blend_color, make_card


def shorten_text(text, limit=24):
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


class MonitorCard(tk.Frame):
    def __init__(self, parent, mic, running, on_start, on_stop, on_remove, **kwargs):
        super().__init__(
            parent,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.mic = mic
        self.running = running
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_remove = on_remove
        self._levels = [0.02] * 42
        self._display_level = 0.0
        self._raw_level = 0.0
        self._active_until = 0.0
        self._phase = 0.0
        self._vibe = 0.0
        self._timer_running = False
        self._timer_start = 0.0
        self._timer_label = ""
        self._timer_timeout = 0
        self._build()
        self._tick_wave()

    def _build(self):
        wrap = tk.Frame(self, bg=COLORS["surface"])
        wrap.pack(fill="both", expand=True, padx=16, pady=14)

        header = tk.Frame(wrap, bg=COLORS["surface"])
        header.pack(fill="x")
        title_wrap = tk.Frame(header, bg=COLORS["surface"])
        title_wrap.pack(side="left", fill="x", expand=True)
        self.title_label = tk.Label(
            title_wrap,
            text=self.mic["name"],
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self.title_label.pack(side="left", fill="x", expand=True)

        self.wave = tk.Canvas(
            header,
            width=92,
            height=22,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        self.wave.pack(side="right", padx=(12, 0))

        self.status_label = tk.Label(wrap, text="Idle", bg=COLORS["surface"], fg=COLORS["muted"], font=(FONT, 1))
        self.timer_label = tk.Label(wrap, text="", bg=COLORS["surface"], fg=COLORS["muted"], font=(FONT, 1))

    def set_running(self, running: bool):
        self.running = running
        if not running and self.status_label.cget("text") == "Waiting to start":
            self.update_status("Idle")

    def update_status(self, text: str):
        tone = COLORS["muted"]
        if "RECORD" in text.upper() or "🎙" in text:
            tone = COLORS["success"]
        elif "TRANSCRIB" in text.upper() or "📝" in text:
            tone = COLORS["primary"]
        elif "ANALYS" in text.upper() or "🤖" in text:
            tone = COLORS["warning"]
        elif "ALERT" in text.upper() or "YES" in text.upper() or "📱" in text:
            tone = COLORS["danger"]
        self.status_label.configure(text=text, fg=tone)

    def push_level(self, level):
        level = max(0.0, level)
        self._levels.pop(0)
        self._raw_level = self._raw_level * 0.65 + level * 0.35
        self._display_level = self._display_level * 0.65 + level * 0.35
        if level >= 0.0015 or self._display_level >= 0.0018:
            self._active_until = time.time() + 0.45
        self._levels.append(max(0.01, min(self._display_level * 340, 1.0)))

    def start_timer(self, label, timeout=0):
        self._timer_label = label
        self._timer_timeout = timeout
        self._timer_start = time.time()
        self._timer_running = True
        self._tick_timer()

    def stop_timer(self):
        self._timer_running = False
        if self.winfo_exists():
            self.timer_label.configure(text="")

    def _tick_timer(self):
        if not self.winfo_exists() or not self._timer_running:
            return
        elapsed = time.time() - self._timer_start
        if self._timer_timeout:
            remaining = max(0, int(self._timer_timeout - elapsed))
            self.timer_label.configure(text=f"{self._timer_label}  {remaining}s left")
        else:
            self.timer_label.configure(text=f"{self._timer_label}  {elapsed:.1f}s")
        self.after(250, self._tick_timer)

    def _tick_wave(self):
        if not self.winfo_exists():
            return
        canvas = self.wave
        canvas.delete("all")
        width = int(canvas.cget("width"))
        height = int(canvas.cget("height"))
        mid = height / 2

        # Keep the idle sweep moving even when the mic is quiet.
        self._phase = (self._phase + 0.06) % 1.0
        self._vibe = (self._vibe + 0.28) % 6.283

        level = sum(self._levels[-6:]) / 6.0 if self._levels else 0.0
        progress = max(4, int(self._phase * (width + 20)) - 10)
        progress = min(width, progress)
        is_active = self.running and (
            self._raw_level >= 0.0015 or time.time() < self._active_until
        )

        base_color = "#d94a60"
        pulse_color = "#2dbf5b"
        if progress > 1:
            if is_active:
                canvas.create_line(
                    0,
                    mid,
                    width,
                    mid,
                    fill="#d7f1df",
                    width=1,
                )
                amp = max(4.0, min(9.0, level * 9.0))
                pulse_center = progress - 16
                points = []
                for x in range(0, progress + 1, 3):
                    y = mid
                    dx = x - pulse_center
                    if -16 <= dx < -7:
                        y = mid
                    elif -7 <= dx < -2:
                        y = mid + amp * 0.35
                    elif -2 <= dx < 2:
                        y = mid - amp * 1.55
                    elif 2 <= dx < 7:
                        y = mid + amp * 0.95
                    elif 7 <= dx < 13:
                        y = mid - amp * 0.28
                    elif 13 <= dx < 18:
                        y = mid
                    y += (level * 7.0) * math.sin(self._vibe + x * 0.28)
                    points.extend([x, max(2, min(height - 2, y))])

                if len(points) < 4:
                    points = [0, mid, progress, mid]

                canvas.create_line(
                    *points,
                    fill=pulse_color,
                    width=2,
                    smooth=True,
                    splinesteps=10,
                    capstyle=tk.ROUND,
                    joinstyle=tk.ROUND,
                )
            else:
                margin = 6
                left_x = margin
                right_x = max(left_x, width - margin)
                sweep_x = left_x + int(self._phase * max(1, right_x - left_x))
                sweep_x = max(left_x, min(right_x, sweep_x))
                if sweep_x > left_x:
                    canvas.create_line(
                        left_x,
                        mid,
                        sweep_x,
                        mid,
                        fill=base_color,
                        width=2,
                        smooth=True,
                        splinesteps=10,
                        joinstyle=tk.ROUND,
                        capstyle=tk.ROUND,
                    )
        self.after(80, self._tick_wave)

class MicActivityView(tk.Frame):
    def __init__(self, parent, mic_name, **kwargs):
        super().__init__(parent, bg=COLORS["surface"], **kwargs)
        self.mic_name = mic_name
        self._build()

    def _build(self):
        self.transcript_text = tk.Text(
            self,
            height=18,
            wrap="word",
            bg=COLORS["surface_soft"],
            fg=COLORS["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(MONO, 9),
        )
        self.transcript_text.pack(fill="both", expand=True)
        self.transcript_text.tag_config("header", foreground=COLORS["primary"], font=(MONO, 9, "bold"))
        self.transcript_text.tag_config("result_yes", foreground=COLORS["danger"], font=(MONO, 9, "bold"))
        self.transcript_text.tag_config("result_no", foreground=COLORS["success"], font=(MONO, 9, "bold"))
        self.transcript_text.tag_config("body", foreground=COLORS["text"], font=(MONO, 9))
        self.transcript_text.tag_config("toxic_stamp", foreground=COLORS["danger"], font=(MONO, 9, "bold"))
        self.transcript_text.configure(state="disabled")

    def reset_view(self):
        self.transcript_text.configure(state="normal")
        self.transcript_text.delete("1.0", "end")
        self.transcript_text.configure(state="disabled")

    def log_activity(self, result, transcript, scores):
        label = "BULLY" if result else "CLEAN"
        toxic_pct = int(scores.get("toxic", 0) * 100)
        ts = time.strftime("%H:%M:%S")
        self.transcript_text.configure(state="normal")
        self.transcript_text.insert("end", f"[{ts}] {self.mic_name}\n", "header")
        self.transcript_text.insert(
            "end",
            f"{label}  toxic={toxic_pct}%\n",
            "result_yes" if result else "result_no",
        )
        self.transcript_text.insert("end", f"{transcript}\n\n", "body")
        self.transcript_text.see("end")
        self.transcript_text.configure(state="disabled")

    def add_toxic_result(self, transcript, scores):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        toxic_pct = int(scores.get("toxic", 0) * 100)
        self.transcript_text.configure(state="normal")
        self.transcript_text.insert("end", f"[TOXIC {ts}] toxic={toxic_pct}%\n", "toxic_stamp")
        self.transcript_text.insert("end", f"{transcript}\n\n", "result_yes")
        self.transcript_text.see("end")
        self.transcript_text.configure(state="disabled")


class MonitorPage(tk.Frame):
    def __init__(self, parent, on_start, on_stop, on_remove, on_back, on_rescan, **kwargs):
        super().__init__(parent, bg=COLORS["app_bg"], **kwargs)
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_remove = on_remove
        self._on_back = on_back
        self._on_rescan = on_rescan
        self.mic_cards = {}
        self.mic_views = {}
        self.tab_buttons = {}
        self.active_tab_id = None
        self._build()

    def _build(self):
        wrap = tk.Frame(self, bg=COLORS["app_bg"])
        wrap.pack(fill="both", expand=True, padx=32, pady=24)

        self.tab_bar_wrap = tk.Frame(wrap, bg=COLORS["app_bg"])
        self.tab_bar_wrap.pack(fill="x")
        self.tab_bar = tk.Frame(self.tab_bar_wrap, bg=COLORS["app_bg"])
        self.tab_bar.pack(fill="x")
        self.tab_join = tk.Frame(wrap, bg=COLORS["border"], height=1)
        self.tab_join.pack(fill="x")

        self.content_card, content_inner = make_card(wrap, padding=18)
        self.content_card.pack(fill="both", expand=True, pady=(0, 0))

        self.monitor_stack = tk.Frame(content_inner, bg=COLORS["surface"], height=44)
        self.monitor_stack.pack_propagate(False)
        self.monitor_stack.pack(fill="x")
        self.monitor_stack.grid_rowconfigure(0, weight=1)
        self.monitor_stack.grid_columnconfigure(0, weight=1)

        self.monitor_empty = tk.Label(
            self.monitor_stack,
            text="No microphone selected",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 10),
            justify="center",
            highlightthickness=0,
        )
        self.monitor_empty.grid(row=0, column=0, sticky="nsew")

        tk.Frame(content_inner, bg=COLORS["surface"], height=14).pack(fill="x")

        self.tab_content = tk.Frame(content_inner, bg=COLORS["surface"])
        self.tab_content.pack(fill="both", expand=True)
        self.tab_content.grid_rowconfigure(0, weight=1)
        self.tab_content.grid_columnconfigure(0, weight=1)

        self.tab_empty = tk.Label(
            self.tab_content,
            text="Select a microphone to see live translation.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 10),
        )
        self.tab_empty.grid(row=0, column=0, sticky="nsew")

    def render_targets(self, targeted, running_ids):
        target_items = list(targeted.items())
        current_ids = {mid for mid, _mic in target_items}

        for mid in list(self.mic_cards.keys()):
            if mid in current_ids:
                continue
            if self.mic_cards[mid].winfo_exists():
                self.mic_cards[mid].destroy()
            self.mic_cards.pop(mid, None)

        for mid, mic in target_items:
            card = self.mic_cards.get(mid)
            if card is None or not card.winfo_exists():
                card = MonitorCard(
                    self.monitor_stack,
                    mic,
                    mid in running_ids,
                    self._on_start,
                    self._on_stop,
                    self._on_remove,
                )
                card.grid(row=0, column=0, sticky="nsew")
                self.mic_cards[mid] = card
            card.set_running(mid in running_ids)

        self._render_tabs(target_items)

    def _render_tabs(self, target_items):
        for child in self.tab_bar.winfo_children():
            child.destroy()

        current_ids = {mid for mid, _mic in target_items}
        for mid in list(self.mic_views.keys()):
            if mid in current_ids:
                continue
            if self.mic_views[mid].winfo_exists():
                self.mic_views[mid].destroy()
            self.mic_views.pop(mid, None)
            self.tab_buttons.pop(mid, None)

        if not target_items:
            self.active_tab_id = None
            if self.monitor_empty.winfo_exists():
                self.monitor_empty.tkraise()
            self.tab_empty.tkraise()
            return

        max_tab_columns = 4
        for index, (mid, mic) in enumerate(target_items):
            if mid not in self.mic_views or not self.mic_views[mid].winfo_exists():
                view = MicActivityView(self.tab_content, mic["name"])
                view.grid(row=0, column=0, sticky="nsew")
                self.mic_views[mid] = view

            button = tk.Button(
                self.tab_bar,
                text=shorten_text(mic["name"], 22),
                bg=COLORS["surface"] if mid == self.active_tab_id else COLORS["surface_alt"],
                fg=COLORS["primary"] if mid == self.active_tab_id else COLORS["text"],
                activebackground=COLORS["surface"],
                activeforeground=COLORS["primary"],
                relief="solid",
                bd=1,
                highlightthickness=1,
                highlightbackground=COLORS["border_strong"] if mid == self.active_tab_id else COLORS["border"],
                font=(FONT, 9, "bold"),
                padx=12,
                pady=6,
                cursor="hand2",
                command=lambda selected_mid=mid: self._activate_tab(selected_mid),
            )
            button.grid(
                row=index // max_tab_columns,
                column=index % max_tab_columns,
                sticky="w",
                padx=(0, 6),
                pady=(0, 0),
            )
            self.tab_buttons[mid] = button

        if self.active_tab_id not in current_ids:
            self.active_tab_id = target_items[0][0]
        self._activate_tab(self.active_tab_id)

    def _activate_tab(self, mic_id):
        if mic_id not in self.mic_views or mic_id not in self.mic_cards:
            return
        self.active_tab_id = mic_id
        self.monitor_empty.lower()
        self.mic_cards[mic_id].tkraise()
        self.mic_views[mic_id].tkraise()
        for mid, button in self.tab_buttons.items():
            is_active = mid == mic_id
            button.configure(
                bg=COLORS["surface"] if is_active else COLORS["surface_alt"],
                fg=COLORS["primary"] if is_active else COLORS["text"],
                highlightbackground=COLORS["border_strong"] if is_active else COLORS["border"],
            )

    def push_level(self, mic_id, level):
        if mic_id in self.mic_cards and self.mic_cards[mic_id].winfo_exists():
            self.mic_cards[mic_id].push_level(level)

    def set_mic_status(self, mic_id, text):
        if mic_id in self.mic_cards and self.mic_cards[mic_id].winfo_exists():
            self.mic_cards[mic_id].update_status(text)

    def start_mic_timer(self, mic_id, label, timeout=0):
        if mic_id in self.mic_cards and self.mic_cards[mic_id].winfo_exists():
            self.mic_cards[mic_id].start_timer(label, timeout)

    def stop_mic_timer(self, mic_id):
        if mic_id in self.mic_cards and self.mic_cards[mic_id].winfo_exists():
            self.mic_cards[mic_id].stop_timer()

    def reset_view(self):
        self.active_tab_id = None
        for view in self.mic_views.values():
            if view.winfo_exists():
                view.destroy()
        self.mic_views = {}
        for card in self.mic_cards.values():
            if card.winfo_exists():
                card.destroy()
        self.mic_cards = {}
        self.tab_buttons = {}
        for child in self.tab_bar.winfo_children():
            child.destroy()
        if self.tab_empty.winfo_exists():
            self.tab_empty.tkraise()
        if self.monitor_empty.winfo_exists():
            self.monitor_empty.tkraise()
        self.render_targets({}, set())

    def log_activity(self, mic_id, name, result, transcript, scores):
        if mic_id not in self.mic_views:
            return
        self.mic_views[mic_id].log_activity(result, transcript, scores)

    def add_result(self, mic_id, name, result, transcript, scores, rec_path=None):
        del name
        del rec_path
        if not result:
            return
        if mic_id not in self.mic_views:
            return
        self.mic_views[mic_id].add_toxic_result(transcript, scores)
        self._activate_tab(mic_id)

"""
Main window controller for the redesigned white-theme UI flow.
"""

import os
import queue
import threading
import time
import tkinter as tk
import ctypes
from ctypes import wintypes
from tkinter import messagebox

from db import init_db, save_detection, save_microphone
from detector import is_toxic, preload_models, transcribe
from recorder import ContinuousRecorder, LevelPreview, get_devices
from telegram_bot import send_alert
from ui.pages.landing_page import LandingPage
from ui.pages.monitor_page import MonitorPage
from ui.pages.scan_page import ScanPage
from ui.theme import COLORS

class MicMonitor:
    def __init__(self, mic, ui_queue):
        self.mic = mic
        self.q = ui_queue
        self.stop = threading.Event()
        self.audio_q = queue.Queue()
        self._thread = None
        self.running = False

    def start(self, on_level):
        if self.running:
            return
        self.stop.clear()
        self.running = True
        rec = ContinuousRecorder(
            device_id=self.mic["device_id"],
            stop_event=self.stop,
            result_queue=self.audio_q,
            on_level=on_level,
            chunk_seconds=8,
        )
        rec.start()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop_now(self):
        self.stop.set()
        self.running = False

    def is_alive(self):
        return self._thread is not None and self._thread.is_alive()

    def _loop(self):
        mid = self.mic["id"]
        name = self.mic["name"]
        chunk_index = 0
        self.q.put(("mic_status", (mid, "Recording")))
        self.q.put(("mic_timer", (mid, "Recording", 8)))

        while not self.stop.is_set():
            try:
                path = self.audio_q.get(timeout=1)
            except queue.Empty:
                continue

            if path is None:
                break

            if self.stop.is_set():
                try:
                    os.remove(path)
                except OSError:
                    pass
                break

            hit_end = False
            while True:
                try:
                    newer = self.audio_q.get_nowait()
                except queue.Empty:
                    break
                if newer is None:
                    self.audio_q.put(None)
                    hit_end = True
                    break
                try:
                    os.remove(path)
                except OSError:
                    pass
                path = newer

            if hit_end and self.stop.is_set():
                break

            chunk_index += 1
            self.q.put(("mic_status", (mid, f"Transcribing clip {chunk_index}")))
            self.q.put(("mic_timer", (mid, "Whisper", 60)))
            transcript = transcribe(path)
            self.q.put(("mic_timer_stop", mid))

            try:
                os.remove(path)
            except OSError:
                pass

            if self.stop.is_set():
                break

            if not transcript or not transcript.strip():
                self.q.put(("mic_status", (mid, "Listening for speech")))
                self.q.put(("mic_timer", (mid, "Recording", 8)))
                continue

            self.q.put(("mic_status", (mid, "Analysing text")))
            self.q.put(("mic_timer", (mid, "BERT", 10)))
            result, scores = is_toxic(transcript)
            self.q.put(("mic_timer_stop", mid))

            if self.stop.is_set():
                break

            self.q.put(("result", {
                "mic_id": mid,
                "name": name,
                "result": result,
                "transcript": transcript,
                "scores": scores,
            }))

            if result:
                send_alert(mic_name=name, transcript=transcript, scores=scores)
                self.q.put(("mic_status", (mid, "Alert sent")))
                time.sleep(0.4)

            if not self.stop.is_set():
                self.q.put(("mic_status", (mid, "Recording")))
                self.q.put(("mic_timer", (mid, "Recording", 8)))

        self.running = False
        self.q.put(("mic_status", (mid, "Stopped")))
        self.q.put(("mic_timer_stop", mid))
        self.q.put(("mic_stopped", mid))


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.devices = []
        self.targeted = {}
        self.monitors = {}
        self.previews = {}
        self.current_page = 0
        self.models_ready = False

        init_db()
        threading.Thread(target=self._load_models_bg, daemon=True).start()

        self._setup_window()
        self._build_chrome()
        self._build_pages()
        self._build_menu_bar()
        self._show_page(0)
        self._process_queue()

    def _setup_window(self):
        self.root.title("BullySpeechDetection")
        self.root.configure(bg=COLORS["app_bg"])
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                self._app_icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, self._app_icon)
            except tk.TclError:
                self._app_icon = None
        width = 900
        height = 660
        work_left = 0
        work_top = 0
        work_w = self.root.winfo_screenwidth()
        work_h = self.root.winfo_screenheight()
        try:
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                work_left = rect.left
                work_top = rect.top
                work_w = rect.right - rect.left
                work_h = rect.bottom - rect.top
        except Exception:
            pass
        pos_x = work_left + max(0, (work_w - width) // 2)
        pos_y = work_top + max(0, (work_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.root.minsize(860, 620)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_chrome(self):
        self.page_area = tk.Frame(self.root, bg=COLORS["app_bg"])
        self.page_area.pack(fill="both", expand=True)

    def _build_menu_bar(self):
        menubar = tk.Menu(self.root)
        menubar.add_command(label="Home", command=self._go_home)
        menubar.add_command(
            label="Help",
            command=lambda: messagebox.showinfo("Help", "BullySpeechDetection"),
        )

        self.root.config(menu=menubar)

    def _build_pages(self):
        self.pages = {
            0: LandingPage(self.page_area, on_start=self._go_to_scan),
            1: ScanPage(
                self.page_area,
                on_scan=self._do_scan,
                on_toggle=self._toggle_target_mic,
                on_start_monitor=lambda: self._go_to_monitor(start_selected=True),
                on_back=lambda: self._show_page(0),
            ),
            2: MonitorPage(
                self.page_area,
                on_start=self._start_monitor,
                on_stop=self._stop_monitor,
                on_remove=self._remove_target,
                on_back=lambda: self._show_page(1),
                on_rescan=self._rescan_from_monitor,
            ),
        }
        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._refresh_target_views()

    def _show_page(self, idx):
        self.current_page = idx
        self.pages[idx].lift()
        self._sync_previews()

    def _set_status(self, text, tone="muted"):
        del text, tone

    def _load_models_bg(self):
        preload_models()
        self.models_ready = True
        self.q.put(("models_ready", None))

    def _on_close(self):
        self._stop_all_previews()
        for monitor in self.monitors.values():
            monitor.stop_now()
        self.root.destroy()

    def _device_selected_ids(self):
        return {mic["device_id"] for mic in self.targeted.values()}

    def _go_home(self):
        self._reset_workflow_state()
        self._show_page(0)

    def _go_to_scan(self):
        self._reset_workflow_state()
        self._show_page(0)
        self._do_scan()

    def _go_to_monitor(self, start_selected=False):
        if not self.targeted:
            self._set_status("Select at least one microphone before monitoring.", "warning")
            self._show_page(1)
            return
        self._stop_all_previews()
        self._refresh_target_views()
        self._show_page(2)
        if start_selected:
            for mic in list(self.targeted.values()):
                self._start_monitor(mic)

    def _rescan_from_monitor(self):
        self._show_page(0)
        self._do_scan()

    def _reset_workflow_state(self):
        self._stop_all_previews()
        for monitor in self.monitors.values():
            monitor.stop_now()
        self.monitors.clear()
        self.targeted.clear()
        self.devices = []
        self.pages[0].set_scanning(False)
        self.pages[1].reset_view()
        self.pages[2].reset_view()

    def _refresh_target_views(self):
        selected_ids = self._device_selected_ids()
        self.pages[1].render_devices(self.devices, selected_ids)
        running_ids = {mid for mid, monitor in self.monitors.items() if monitor.is_alive()}
        self.pages[2].render_targets(self.targeted, running_ids)
        self._sync_previews()

    def _stop_all_previews(self):
        for preview in self.previews.values():
            preview.stop_now()
        self.previews.clear()

    def _sync_previews(self):
        if self.current_page != 1:
            self._stop_all_previews()
            return

        selected_ids = self._device_selected_ids()
        for device_id in list(self.previews.keys()):
            if device_id not in selected_ids:
                self.previews[device_id].stop_now()
                self.previews.pop(device_id, None)
                self.pages[1].update_preview_level(device_id, 0.0)

        for device_id in selected_ids:
            if device_id in self.previews:
                continue
            preview = LevelPreview(
                device_id,
                lambda level, did=device_id: self.q.put(("preview_level", (did, level))),
            )
            preview.start()
            self.previews[device_id] = preview

    def _do_scan(self):
        self._show_page(0)
        self.pages[0].set_scanning(True)
        self.pages[1].set_scanning(True)
        self._set_status("Scanning microphones...", "warning")

        def worker():
            started_at = time.time()
            devices = get_devices()
            remaining = 5.0 - (time.time() - started_at)
            if remaining > 0:
                time.sleep(remaining)
            self.q.put(("scan_done", devices))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_done(self, devices):
        self.devices = devices
        self.pages[0].set_scanning(False)
        self.pages[1].set_scanning(False)
        self._refresh_target_views()
        self._show_page(1)
        if devices:
            self.pages[1].set_status(f"Found {len(devices)} microphone(s). Select the devices to monitor.", "success")
            self._set_status(f"Found {len(devices)} microphone(s).", "success")
        else:
            self.pages[1].set_status("No microphones found. Check your audio device connection and rescan.", "danger")
            self._set_status("No microphones found.", "danger")

    def _toggle_target_mic(self, dev):
        existing_id = next((mid for mid, mic in self.targeted.items() if mic["device_id"] == dev["id"]), None)
        if existing_id is not None:
            if existing_id in self.monitors and self.monitors[existing_id].is_alive():
                self._set_status("Stop the active monitor before removing it.", "warning")
                return
            self.targeted.pop(existing_id, None)
            self._set_status(f"Unselected {dev['name']}", "muted")
        else:
            mic = save_microphone(device_id=dev["id"], name=dev["name"])
            self.targeted[mic["id"]] = mic
            self._set_status(f"Selected {dev['name']}", "success")
        self._refresh_target_views()

    def _remove_target(self, mic_id):
        if mic_id in self.monitors and self.monitors[mic_id].is_alive():
            self._set_status("Stop the active monitor before removing it.", "warning")
            return
        mic = self.targeted.pop(mic_id, None)
        if mic is not None:
            self._set_status(f"Removed {mic['name']}", "muted")
        self._refresh_target_views()

    def _start_monitor(self, mic):
        mid = mic["id"]
        if not self.models_ready:
            self._set_status("Models are still loading. The monitor will start shortly.", "warning")
            self.pages[2].set_mic_status(mid, "Waiting to start")
            self.root.after(1500, lambda: self._start_monitor(mic))
            return
        if mid in self.monitors and self.monitors[mid].is_alive():
            return

        monitor = MicMonitor(mic, self.q)

        def on_level(level, _mid=mid):
            self.q.put(("monitor_level", (_mid, level)))

        monitor.start(on_level)
        self.monitors[mid] = monitor
        self.pages[2].render_targets(self.targeted, {k for k, v in self.monitors.items() if v.is_alive()})
        self.pages[2].set_mic_status(mid, "Recording")
        self._set_status(f"Monitoring {mic['name']}", "primary")

    def _stop_monitor(self, mic_id):
        if mic_id not in self.monitors:
            return
        self.monitors[mic_id].stop_now()
        self.pages[2].set_mic_status(mic_id, "Stopping")
        self.pages[2].stop_mic_timer(mic_id)
        self.pages[2].render_targets(self.targeted, {k for k, v in self.monitors.items() if v.is_alive()})
        self._set_status("Stopping monitor...", "warning")

    def _process_queue(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "models_ready":
                    self._set_status("Models ready", "success")
                elif kind == "scan_done":
                    self._on_scan_done(data)
                elif kind == "mic_status":
                    mid, text = data
                    self.pages[2].set_mic_status(mid, text)
                elif kind == "mic_timer":
                    mid, label, timeout = data
                    self.pages[2].start_mic_timer(mid, label, timeout)
                elif kind == "mic_timer_stop":
                    self.pages[2].stop_mic_timer(data)
                elif kind == "mic_stopped":
                    self.pages[2].set_mic_status(data, "Stopped")
                    self.pages[2].render_targets(self.targeted, {k for k, v in self.monitors.items() if v.is_alive()})
                    if not any(monitor.is_alive() for monitor in self.monitors.values()):
                        self._set_status("Ready", "muted")
                elif kind == "result":
                    self._on_result(data)
                elif kind == "preview_level":
                    device_id, level = data
                    self.pages[1].update_preview_level(device_id, level)
                elif kind == "monitor_level":
                    mic_id, level = data
                    self.pages[2].push_level(mic_id, level)
        except queue.Empty:
            pass
        self.root.after(40, self._process_queue)

    def _on_result(self, data):
        save_detection(
            mic_id=data["mic_id"],
            transcript=data["transcript"],
            result="YES" if data["result"] else "NO",
            scores=data["scores"],
            alerted=data["result"],
            recording_path=None,
        )
        self.pages[2].log_activity(data["mic_id"], data["name"], data["result"], data["transcript"], data["scores"])
        self.pages[2].add_result(data["mic_id"], data["name"], data["result"], data["transcript"], data["scores"])
        if data["result"]:
            self._set_status("Bully speech detected", "danger")

import os
import math
import tkinter as tk

from ui.components import AppButton
from ui.theme import COLORS, FONT, make_card


class HoverTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip,
            text=self.text,
            bg=COLORS["text"],
            fg=COLORS["surface"],
            font=(FONT, 9),
            padx=8,
            pady=4,
        )
        label.pack()

    def _hide(self, _event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class IconButton(tk.Label):
    def __init__(self, parent, image, command, tooltip, disabled_image=None, **kwargs):
        super().__init__(
            parent,
            image=image,
            bg=kwargs.pop("bg", parent.cget("bg")),
            cursor="hand2",
            **kwargs,
        )
        self._default_bg = self.cget("bg")
        self._command = command
        self._enabled = True
        self._image = image
        self._disabled_image = disabled_image or image
        self.configure(padx=4, pady=4)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        HoverTip(self, tooltip)

    def _on_click(self, _event):
        if self._enabled and callable(self._command):
            self._command()

    def _on_enter(self, _event):
        if self._enabled:
            self.configure(bg=COLORS["surface_soft"])

    def _on_leave(self, _event):
        self.configure(bg=self._default_bg)

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.configure(
            image=self._image if enabled else self._disabled_image,
            cursor="hand2" if enabled else "arrow",
        )
        self._on_leave(None)


class ScanPage(tk.Frame):
    def __init__(self, parent, on_scan, on_toggle, on_start_monitor, on_back, **kwargs):
        super().__init__(parent, bg=COLORS["app_bg"], **kwargs)
        self._on_scan = on_scan
        self._on_toggle = on_toggle
        self._on_start_monitor = on_start_monitor
        self._on_back = on_back
        self._selected_count = 0
        self._selected_ids = set()
        self._devices = []
        self._checked_icon = None
        self._unchecked_icon = None
        self._back_icon = None
        self._prev_icon = None
        self._next_icon = None
        self._prev_disabled_icon = None
        self._next_disabled_icon = None
        self._page_index = 0
        self._page_size = 4
        self._preview_levels = {}
        self._row_widgets = {}
        self._column_widths = {
            0: 330,
            1: 90,
            2: 116,
            3: 76,
            4: 180,
        }
        self._row_height = 68
        self._load_toggle_icons()
        self._build()
        self.after(70, self._animate_heartbeats)

    def _load_toggle_icons(self):
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        checked_path = os.path.join(assets_dir, "checked.png")
        unchecked_path = os.path.join(assets_dir, "unchecked.png")
        back_path = os.path.join(assets_dir, "back_arrow.png")
        prev_path = os.path.join(assets_dir, "pagination_previous_arrow.png")
        next_path = os.path.join(assets_dir, "pagination_next_arrow.png")
        try:
            if os.path.exists(checked_path):
                self._checked_icon = tk.PhotoImage(file=checked_path).subsample(16, 16)
            if os.path.exists(unchecked_path):
                self._unchecked_icon = tk.PhotoImage(file=unchecked_path).subsample(16, 16)
            if os.path.exists(back_path):
                self._back_icon = tk.PhotoImage(file=back_path).subsample(14, 14)
            if os.path.exists(prev_path):
                self._prev_icon = tk.PhotoImage(file=prev_path).subsample(14, 14)
                self._prev_disabled_icon = self._prev_icon
            if os.path.exists(next_path):
                self._next_icon = tk.PhotoImage(file=next_path).subsample(14, 14)
                self._next_disabled_icon = self._next_icon
        except tk.TclError:
            self._checked_icon = None
            self._unchecked_icon = None
            self._back_icon = None
            self._prev_icon = None
            self._next_icon = None
            self._prev_disabled_icon = None
            self._next_disabled_icon = None

    def _build(self):
        wrap = tk.Frame(self, bg=COLORS["app_bg"], width=860, height=520)
        wrap.place(relx=0.5, rely=0.08, anchor="n")
        wrap.pack_propagate(False)

        header = tk.Frame(wrap, bg=COLORS["app_bg"])
        header.pack(fill="x", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        title_wrap = tk.Frame(header, bg=COLORS["app_bg"])
        title_wrap.grid(row=0, column=0)
        tk.Label(
            title_wrap,
            text="Detected Microphones",
            bg=COLORS["app_bg"],
            fg=COLORS["text"],
            font=(FONT, 15, "bold"),
        ).pack(anchor="center")
        tk.Label(
            title_wrap,
            text="Select the devices you want to monitor.",
            bg=COLORS["app_bg"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(anchor="center", pady=(2, 0))

        self.list_card, list_inner = make_card(wrap, padding=14)
        self.list_card.pack(fill="both", expand=True, anchor="n")
        stats_row = tk.Frame(list_inner, bg=COLORS["surface"])
        stats_row.pack(fill="x", pady=(0, 8))
        self.total_label = tk.Label(stats_row, text="Total: 0", bg=COLORS["surface"], fg=COLORS["text"], font=(FONT, 10, "bold"))
        self.total_label.pack(side="left")
        self.selected_label = tk.Label(stats_row, text="Selected: 0", bg=COLORS["surface"], fg=COLORS["text"], font=(FONT, 10, "bold"))
        self.selected_label.pack(side="left", padx=(18, 0))
        self.start_button_slot = tk.Frame(stats_row, bg=COLORS["surface"], width=170, height=44)
        self.start_button_slot.pack(side="right")
        self.start_button_slot.pack_propagate(False)
        self.start_button = AppButton(
            self.start_button_slot,
            "Start Monitor",
            self._on_start_monitor,
            variant="success",
            state="normal",
            pady=8,
        )

        self.device_table = tk.Frame(list_inner, bg=COLORS["surface"])
        self.device_table.pack(fill="x")
        self._build_table_header(self.device_table)
        self.device_list_host = tk.Frame(
            self.device_table,
            bg=COLORS["surface"],
            height=self._row_height * self._page_size + 1,
        )
        self.device_list_host.pack(fill="x")
        self.device_list_host.pack_propagate(False)
        self.device_list = tk.Frame(self.device_list_host, bg=COLORS["surface"])
        self.device_list.place(relx=0, rely=0, relwidth=1, relheight=1)

        pager = tk.Frame(list_inner, bg=COLORS["surface"])
        pager.pack(fill="x", pady=(18, 0))
        pager.grid_columnconfigure(0, weight=1)
        pager.grid_columnconfigure(1, weight=1)
        pager.grid_columnconfigure(2, weight=1)

        pager_actions = tk.Frame(pager, bg=COLORS["surface"])
        pager_actions.grid(row=0, column=1)
        self.prev_button = self._build_pager_action(pager_actions, self._prev_icon, "Previous Page", self._go_previous_page)
        self.prev_button.pack(side="left", padx=(0, 6))
        self.page_label = tk.Label(pager_actions, text="Page 0 / 0", bg=COLORS["surface"], fg=COLORS["muted"], font=(FONT, 9, "bold"))
        self.page_label.pack(side="left", padx=8)
        self.next_button = self._build_pager_action(pager_actions, self._next_icon, "Next Page", self._go_next_page)
        self.next_button.pack(side="left")

    def _handle_scan(self):
        self._on_scan()

    def set_scanning(self, scanning: bool):
        if scanning:
            self.total_label.configure(text="Total: --")
            self.selected_label.configure(text="Selected: --")

    def set_status(self, text: str, tone="muted"):
        self._update_counts()

    def reset_view(self):
        self._devices = []
        self._selected_ids = set()
        self._selected_count = 0
        self._page_index = 0
        self._preview_levels = {}
        self._row_widgets = {}
        self.total_label.configure(text="Total: 0")
        self.selected_label.configure(text="Selected: 0")
        if self.start_button.winfo_manager():
            self.start_button.pack_forget()
        for child in self.device_list.winfo_children():
            child.destroy()
        for _ in range(self._page_size):
            self._add_empty_row()
        self._update_pagination_controls()

    def render_devices(self, devices, selected_ids):
        self._devices = list(devices)
        self._selected_ids = set(selected_ids)
        self._selected_count = len(selected_ids)
        self._row_widgets = {}
        page_count = self._page_count()
        if page_count == 0:
            self._page_index = 0
        else:
            self._page_index = min(self._page_index, page_count - 1)
        for child in self.device_list.winfo_children():
            child.destroy()

        if not devices:
            tk.Label(self.device_list, text="No microphones detected.", bg=COLORS["surface"], fg=COLORS["muted"], font=(FONT, 10), pady=24).pack()
        else:
            start = self._page_index * self._page_size
            end = start + self._page_size
            page_devices = devices[start:end]
            for dev in page_devices:
                self._add_device_row(dev, dev["id"] in self._selected_ids)
            for _ in range(self._page_size - len(page_devices)):
                self._add_empty_row()

        self._update_counts()
        selected_devices = [dev for dev in devices if dev["id"] in selected_ids]
        if selected_devices:
            if not self.start_button.winfo_manager():
                self.start_button.pack(side="right")
        else:
            if self.start_button.winfo_manager():
                self.start_button.pack_forget()
        self._update_pagination_controls()

    def _build_table_header(self, parent):
        header = tk.Frame(parent, bg=COLORS["surface_alt"], highlightthickness=1, highlightbackground=COLORS["border"])
        header.pack(fill="x", pady=(0, 0))
        columns = [
            ("Microphone", 0, "w", 4),
            ("Device ID", 1, "w", 0),
            ("Sample Rate", 2, "w", 0),
            ("Channels", 3, "w", 0),
            ("Action", 4, "", 0),
        ]
        self._configure_table_columns(header)
        for text, column, sticky, padx in columns:
            tk.Label(
                header,
                text=text,
                bg=COLORS["surface_alt"],
                fg=COLORS["muted"],
                font=(FONT, 9, "bold"),
                padx=12 if column == 0 else 8,
                pady=8,
            ).grid(row=0, column=column, sticky=sticky, padx=(padx, 0))

    def _add_device_row(self, dev, selected):
        row = tk.Frame(
            self.device_list,
            bg=COLORS["surface"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            height=self._row_height,
        )
        row.pack(fill="x", pady=0)
        row.pack_propagate(False)
        self._configure_table_columns(row)

        tk.Label(
            row,
            text=dev["name"],
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=self._column_widths[0] - 32,
            padx=12,
            pady=8,
        ).grid(row=0, column=0, sticky="nw")
        tk.Label(
            row,
            text=str(dev["id"]),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor="w",
            padx=8,
            pady=8,
        ).grid(row=0, column=1, sticky="nw")
        tk.Label(
            row,
            text=f"{dev['rate']} Hz",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor="w",
            padx=8,
            pady=8,
        ).grid(row=0, column=2, sticky="nw")
        tk.Label(
            row,
            text=str(dev["channels"]),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            anchor="w",
            padx=8,
            pady=8,
        ).grid(row=0, column=3, sticky="nw")

        action_cell = tk.Frame(
            row,
            bg=COLORS["surface"],
            width=self._column_widths[4],
            height=self._row_height,
        )
        action_cell.grid(row=0, column=4, sticky="nsew")
        action_cell.grid_propagate(False)

        checkbox_x = 44
        heartbeat_x = 82

        heartbeat = tk.Canvas(
            action_cell,
            width=84,
            height=22,
            bg=COLORS["surface"],
            bd=0,
            highlightthickness=0,
        )
        heartbeat.place(x=heartbeat_x, rely=0.5, anchor="w")

        if self._checked_icon is not None and self._unchecked_icon is not None:
            icon = self._checked_icon if selected else self._unchecked_icon
            icon_button = tk.Button(
                action_cell,
                image=icon,
                command=lambda d=dev: self._on_toggle(d),
                bg=COLORS["surface"],
                activebackground=COLORS["surface"],
                bd=0,
                relief="flat",
                highlightthickness=0,
                cursor="hand2",
            )
            icon_button.place(x=checkbox_x, rely=0.5, anchor="center")
        else:
            btn = AppButton(
                action_cell,
                "",
                lambda d=dev: self._on_toggle(d),
                variant="ghost",
            )
            btn.place(x=checkbox_x, rely=0.5, anchor="center")

        self._row_widgets[dev["id"]] = {
            "canvas": heartbeat,
            "selected": selected,
            "phase": 0.0,
            "vibe": 0.0,
        }
        self._draw_heartbeat(dev["id"])

        # Keep the bottom border visible across the full row, including the action cell.
        tk.Frame(row, bg=COLORS["border"], height=1, bd=0).place(
            x=0,
            rely=1.0,
            relwidth=1.0,
            anchor="sw",
        )

    def _add_empty_row(self):
        row = tk.Frame(
            self.device_list,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
            height=self._row_height,
        )
        row.pack(fill="x", pady=0)
        row.pack_propagate(False)
        self._configure_table_columns(row)
        for column in range(5):
            tk.Label(
                row,
                text="",
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=(FONT, 9),
                padx=8,
                pady=10,
            ).grid(row=0, column=column, sticky="w")

    def _configure_table_columns(self, widget):
        for column, width in self._column_widths.items():
            widget.grid_columnconfigure(column, minsize=width, weight=0)

    def update_preview_level(self, device_id, level):
        current = self._preview_levels.get(device_id, 0.0)
        smoothed = current * 0.65 + level * 0.35
        self._preview_levels[device_id] = smoothed
        if device_id in self._row_widgets:
            self._draw_heartbeat(device_id)

    def _animate_heartbeats(self):
        for device_id, info in list(self._row_widgets.items()):
            if info["selected"]:
                info["phase"] = (info["phase"] + 0.05) % 1.0
                info["vibe"] = (info["vibe"] + 0.28) % 6.283
                self._draw_heartbeat(device_id)
        self.after(70, self._animate_heartbeats)

    def _draw_heartbeat(self, device_id):
        info = self._row_widgets.get(device_id)
        if not info:
            return
        canvas = info["canvas"]
        canvas.delete("all")

        width = int(canvas.cget("width"))
        height = int(canvas.cget("height"))
        mid_y = height / 2

        if not info["selected"]:
            return

        level = self._preview_levels.get(device_id, 0.0)
        progress = max(4, int(info["phase"] * (width + 20)) - 10)
        progress = min(width, progress)
        if progress <= 1:
            return

        is_active = level >= 0.004
        base_color = "#d94a60"
        pulse_color = "#2dbf5b"
        amp = max(4.0, min(9.0, level * 340.0))
        pulse_center = progress - 16

        points = []
        for x in range(0, progress + 1, 3):
            y = mid_y
            if is_active:
                dx = x - pulse_center
                if -16 <= dx < -7:
                    y = mid_y
                elif -7 <= dx < -2:
                    y = mid_y + amp * 0.35
                elif -2 <= dx < 2:
                    y = mid_y - amp * 1.55
                elif 2 <= dx < 7:
                    y = mid_y + amp * 0.95
                elif 7 <= dx < 13:
                    y = mid_y - amp * 0.28
                elif 13 <= dx < 18:
                    y = mid_y
                if x <= progress:
                    y += (level * 55.0) * math.sin(info["vibe"] + x * 0.28)
            points.extend([x, max(2, min(height - 2, y))])

        if len(points) < 4:
            points = [0, mid_y, progress, mid_y]

        canvas.create_line(
            0,
            mid_y,
            width,
            mid_y,
            fill="#f1d8dd" if not is_active else "#d7f1df",
            width=1,
        )
        if is_active:
            vibe_points = []
            for idx in range(0, len(points), 2):
                vibe_points.extend([points[idx], max(2, min(height - 2, points[idx + 1] + 1.4))])
            canvas.create_line(
                *vibe_points,
                fill="#84dca2",
                width=1,
                smooth=True,
                splinesteps=10,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
        canvas.create_line(
            *points,
            fill=pulse_color if is_active else base_color,
            width=2,
            smooth=True,
            splinesteps=10,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
        )

    def _update_counts(self):
        self.total_label.configure(text=f"Total: {len(self._devices)}")
        self.selected_label.configure(text=f"Selected: {self._selected_count}")

    def _page_count(self):
        if not self._devices:
            return 0
        return (len(self._devices) + self._page_size - 1) // self._page_size

    def _update_pagination_controls(self):
        page_count = self._page_count()
        if page_count == 0:
            self.page_label.configure(text="Page 0 / 0")
            self.prev_button.set_enabled(False)
            self.next_button.set_enabled(False)
            return
        self.page_label.configure(text=f"Page {self._page_index + 1} / {page_count}")
        self.prev_button.set_enabled(self._page_index > 0)
        self.next_button.set_enabled(self._page_index < page_count - 1)

    def _go_previous_page(self):
        if self._page_index <= 0:
            return
        self._page_index -= 1
        self.render_devices(self._devices, self._selected_ids)

    def _go_next_page(self):
        if self._page_index >= self._page_count() - 1:
            return
        self._page_index += 1
        self.render_devices(self._devices, self._selected_ids)

    def _build_pager_action(self, parent, icon, tooltip, command):
        if icon is not None:
            return IconButton(parent, icon, command, tooltip, bg=COLORS["surface"])
        return AppButton(parent, tooltip, command, variant="ghost")

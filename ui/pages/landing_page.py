import os
import tkinter as tk
from collections import deque

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - Pillow is expected in the app env
    Image = None
    ImageTk = None

from ui.components import AppButton
from ui.theme import COLORS, FONT, blend_color


class LandingPage(tk.Frame):
    def __init__(self, parent, on_start, **kwargs):
        super().__init__(parent, bg=COLORS["app_bg"], **kwargs)
        self._on_start = on_start
        self._scanning = False
        self._loading_phase = 0
        self._hero_source = None
        self._hero_photo = None
        self._loading_source = None
        self._loading_photo = None
        self._hero_asset_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets",
            "home_page_image.png",
        )
        self._loading_asset_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets",
            "loading_image.png",
        )
        if Image is not None and os.path.exists(self._hero_asset_path):
            try:
                loaded = Image.open(self._hero_asset_path).convert("RGBA")
                self._hero_source = self._merge_hero_background(loaded)
            except Exception:
                self._hero_source = None
        if Image is not None and os.path.exists(self._loading_asset_path):
            try:
                loaded = Image.open(self._loading_asset_path).convert("RGBA")
                self._loading_source = self._merge_hero_background(loaded)
            except Exception:
                self._loading_source = None
        self._build()
        self.bind("<Configure>", self._on_resize)

    def _build(self):
        self.content = tk.Frame(self, bg=COLORS["app_bg"])
        self.content.place(relx=0.5, rely=0.5, anchor="center")

        self.hero_panel = tk.Frame(
            self.content,
            bg=COLORS["surface_soft"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            bd=0,
        )
        self.hero_panel.pack()

        self.hero_inner = tk.Frame(self.hero_panel, bg=COLORS["surface_soft"])
        self.hero_inner.pack(fill="both", expand=True, padx=24, pady=24)
        self.hero_inner.grid_columnconfigure(0, weight=1)
        self.hero_inner.grid_columnconfigure(1, weight=1)

        left = tk.Frame(self.hero_inner, bg=COLORS["surface_soft"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))

        tk.Label(
            left,
            text="AI Powered",
            bg=COLORS["primary_soft"],
            fg=COLORS["primary"],
            font=(FONT, 9, "bold"),
            padx=12,
            pady=6,
        ).pack(anchor="w")

        title_wrap = tk.Frame(left, bg=COLORS["surface_soft"])
        title_wrap.pack(anchor="w", pady=(18, 0))
        for text in ("Bully", "Speech", "Detection"):
            tk.Label(
                title_wrap,
                text=text,
                bg=COLORS["surface_soft"],
                fg=COLORS["text"],
                font=(FONT, 24, "bold"),
                anchor="w",
            ).pack(anchor="w")

        tk.Label(
            left,
            text="Monitor microphones, scan live speech, and detect toxic bully language in one flow.",
            bg=COLORS["surface_soft"],
            fg=COLORS["muted"],
            font=(FONT, 10),
            justify="left",
            wraplength=270,
        ).pack(anchor="w", pady=(16, 0))

        AppButton(
            left,
            "Scan",
            self._on_start,
            font=(FONT, 11, "bold"),
            padx=24,
            pady=11,
        ).pack(anchor="w", pady=(26, 0))

        right = tk.Frame(self.hero_inner, bg=COLORS["surface_soft"])
        right.grid(row=0, column=1, sticky="nsew")
        self.hero_image_label = tk.Label(
            right,
            bg=COLORS["surface_soft"],
            bd=0,
            highlightthickness=0,
        )
        self.hero_image_label.pack(fill="both", expand=True)

        self.overlay = tk.Frame(self, bg=COLORS["surface_soft"])
        self.overlay_panel = tk.Frame(
            self.overlay,
            bg=COLORS["surface"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            bd=0,
        )
        self.overlay_panel.place(relx=0.5, rely=0.5, anchor="center")

        self.overlay_inner = tk.Frame(self.overlay_panel, bg=COLORS["surface"])
        self.overlay_inner.pack(fill="both", expand=True, padx=26, pady=26)
        self.overlay_title = tk.Label(
            self.overlay_inner,
            text="Scanning",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(FONT, 22, "bold"),
        )
        self.overlay_title.pack(pady=(2, 0))
        self.loading_image_label = tk.Label(
            self.overlay_inner,
            bg=COLORS["surface"],
            bd=0,
            highlightthickness=0,
        )
        self.loading_image_label.pack(pady=(16, 14))
        self.spinner = tk.Canvas(
            self.overlay_inner,
            width=320,
            height=48,
            bg=COLORS["surface"],
            highlightthickness=0,
        )
        self.spinner.pack()

    def set_scanning(self, scanning: bool):
        self._scanning = scanning
        if scanning:
            self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.overlay.tkraise()
            self.content.lower()
            self._draw_overlay()
            self._animate_overlay()
        else:
            self.overlay.place_forget()
            self.content.tkraise()

    def _on_resize(self, _event):
        self._refresh_layout()
        if self._scanning:
            self._draw_overlay()

    def _refresh_layout(self):
        width = max(720, self.winfo_width())
        panel_width = min(820, max(720, width - 70))
        panel_height = 430
        self.hero_panel.configure(width=panel_width, height=panel_height)
        self.hero_panel.pack_propagate(False)
        self._refresh_hero_image(panel_width)
        overlay_width = min(620, max(500, width - 180))
        overlay_height = 500
        self.overlay_panel.configure(width=overlay_width, height=overlay_height)
        self.overlay_panel.pack_propagate(False)
        self._refresh_loading_image(overlay_width, overlay_height)

    def _refresh_hero_image(self, panel_width):
        if self._hero_source is None or Image is None or ImageTk is None:
            self.hero_image_label.configure(image="", text="")
            return

        target_width = max(280, min(430, int(panel_width * 0.46)))
        source_w, source_h = self._hero_source.size
        ratio = target_width / float(source_w)
        target_height = max(220, int(source_h * ratio))
        resized = self._hero_source.resize((target_width, target_height), Image.LANCZOS)
        self._hero_photo = ImageTk.PhotoImage(resized)
        self.hero_image_label.configure(image=self._hero_photo)

    def _refresh_loading_image(self, overlay_width, overlay_height):
        if self._loading_source is None or Image is None or ImageTk is None:
            self.loading_image_label.configure(image="", text="")
            return

        source_w, source_h = self._loading_source.size
        max_width = max(260, min(360, int(overlay_width * 0.66)))
        # Reserve room for title, paddings, and the small loading animation below.
        max_height = max(210, overlay_height - 170)
        ratio = min(max_width / float(source_w), max_height / float(source_h))
        target_width = max(240, int(source_w * ratio))
        target_height = max(190, int(source_h * ratio))
        resized = self._loading_source.resize((target_width, target_height), Image.LANCZOS)
        self._loading_photo = ImageTk.PhotoImage(resized)
        self.loading_image_label.configure(image=self._loading_photo)

    def _merge_hero_background(self, image):
        working = image.copy()
        pixels = working.load()
        width, height = working.size
        visited = set()
        queue = deque()

        def is_bg(px):
            r, g, b, a = px
            return a > 0 and r >= 245 and g >= 245 and b >= 245

        for x in range(width):
            queue.append((x, 0))
            queue.append((x, height - 1))
        for y in range(height):
            queue.append((0, y))
            queue.append((width - 1, y))

        while queue:
            x, y = queue.popleft()
            if (x, y) in visited or not (0 <= x < width and 0 <= y < height):
                continue
            visited.add((x, y))
            if not is_bg(pixels[x, y]):
                continue
            pixels[x, y] = (255, 255, 255, 0)
            queue.append((x + 1, y))
            queue.append((x - 1, y))
            queue.append((x, y + 1))
            queue.append((x, y - 1))

        bg_hex = COLORS["surface_soft"]
        bg_rgb = tuple(int(bg_hex[i:i + 2], 16) for i in (1, 3, 5))
        background = Image.new("RGBA", working.size, bg_rgb + (255,))
        return Image.alpha_composite(background, working)

    def _draw_overlay(self):
        self.spinner.delete("all")
        self.spinner.configure(bg=COLORS["surface"])

    def _animate_overlay(self):
        if not self._scanning or not self.winfo_exists():
            return
        self._draw_overlay()
        cx = 160
        bar_y = 10
        bar_w = 10
        gap = 3
        total = 18
        start_x = cx - ((bar_w + gap) * total - gap) / 2
        active_index = self._loading_phase % total
        for idx in range(total):
            distance = (idx - active_index) % total
            alpha = max(0.18, 1.0 - distance * 0.14)
            fill = blend_color(COLORS["primary"], COLORS["surface"], alpha)
            self.spinner.create_rectangle(
                start_x + idx * (bar_w + gap),
                bar_y,
                start_x + idx * (bar_w + gap) + bar_w,
                bar_y + 18,
                fill=fill,
                outline=COLORS["primary"],
                width=1,
            )

        self._loading_phase = (self._loading_phase + 1) % total
        self.after(70, self._animate_overlay)

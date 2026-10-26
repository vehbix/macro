"""Konum/renk seçici (X tuşu) ve ekrandan resim yakalama."""
import base64
import tkinter as tk

from pynput.keyboard import Key, KeyCode

from ..actions import XY_KEYS
from ..core.cv import HAS_CV, np, cv2
from ..core.screen import _screen_pixel, capture_screen
from ..core.utils import _cursor_pos
from ..core.winapi import user32
from .theme import AMBER, AMBER_H, FONT


class PickerMixin:
    # ================= KONUM / RENK SEÇİCİ =================
    def start_picker(self, key):
        self.is_picking = key
        for k in self._pick_buttons:
            if k != key:
                self._reset_pick_button(k)
        b = self._pick_buttons.get(key)
        if b:
            b.configure(text="Fareyi hedefe götür ve X'e bas…", fg_color=AMBER, hover_color=AMBER_H,
                        text_color="#1f1606", border_width=0)
        self.set_status("Seçim modu: imleci hedefe götür, X tuşuna bas. İptal için Esc.", "warn")

    def on_picker_key(self, key):
        # pynput thread'i — tkinter'a sadece root.after ile dokunulur
        mode = self.is_picking
        if not mode: return
        if key == Key.esc:
            self.is_picking = False
            self.root.after(0, lambda: (self._reset_pick_button(mode), self.set_status("Seçim iptal edildi.", "info", 2000)))
            return
        if not isinstance(key, KeyCode) or not key.char or key.char.lower() != "x":
            return
        self.is_picking = False
        x, y = _cursor_pos()
        pixel = _screen_pixel(x, y) if mode == "color" else None
        self.root.after(0, lambda: self._apply_pick(mode, x, y, pixel))

    def _apply_pick(self, mode, x, y, pixel):
        if self.use_window_mode.get():
            win = self.get_window_rect()
            if win: x -= win.left; y -= win.top
        kx, ky = XY_KEYS.get("xy2" if mode == "xy2" else "xy")
        self._var(kx).set(str(x)); self._var(ky).set(str(y))
        msg = f"Konum alındı: {x}, {y}"
        if mode == "color":
            if pixel is None:
                self.set_status("Renk okunamadı.", "error", 3000)
            else:
                self._var("color").set(f"{pixel[0]},{pixel[1]},{pixel[2]}")
                msg += f"  ·  renk {pixel[0]},{pixel[1]},{pixel[2]}"
        self._reset_pick_button(mode)
        self.set_status(msg, "ok", 3500)

    # ================= RESİM YAKALAMA =================
    def capture_template(self):
        if not HAS_CV:
            self.set_status("Resim Bul için: pip install opencv-python numpy", "error", 5000)
            return
        self.root.iconify()
        self.root.after(350, self._open_capture_overlay)

    def _open_capture_overlay(self):
        vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
        vw, vh = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
        ov = tk.Toplevel(self.root)
        ov.overrideredirect(True)
        ov.geometry(f"{vw}x{vh}+{vx}+{vy}")
        ov.attributes("-topmost", True)
        ov.attributes("-alpha", 0.35)
        cv = tk.Canvas(ov, bg="black", highlightthickness=0, cursor="crosshair")
        cv.pack(fill="both", expand=True)
        cx, cy = _cursor_pos()
        cv.create_text(cx - vx, cy - vy - 40, fill="white", font=(FONT, 16, "bold"),
                       text="Aranacak alanı fareyle sürükleyerek seç  ·  İptal: Esc")
        state = {}

        def press(e):
            state["x0"], state["y0"] = e.x_root, e.y_root
            state["rect"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#6c8cff", width=2, fill="white")

        def drag(e):
            if "rect" in state:
                cv.coords(state["rect"], state["x0"] - vx, state["y0"] - vy, e.x, e.y)

        def finish(e=None, cancel=False):
            ov.destroy()
            if cancel or "x0" not in state or e is None:
                self.root.deiconify()
                self.set_status("Resim seçimi iptal edildi.", "info", 2000)
                return
            x0, y0 = min(state["x0"], e.x_root), min(state["y0"], e.y_root)
            x1, y1 = max(state["x0"], e.x_root), max(state["y0"], e.y_root)
            self.root.after(150, lambda: self._finish_capture(x0, y0, x1, y1))

        cv.bind("<ButtonPress-1>", press)
        cv.bind("<B1-Motion>", drag)
        cv.bind("<ButtonRelease-1>", lambda e: finish(e))
        ov.bind("<Escape>", lambda e: finish(cancel=True))
        ov.focus_force()

    def _finish_capture(self, x0, y0, x1, y1):
        try:
            if x1 - x0 < 4 or y1 - y0 < 4:
                raise ValueError("Seçilen alan çok küçük.")
            img, vx, vy = capture_screen()
            if img is None:
                raise ValueError("Ekran görüntüsü alınamadı.")
            crop = np.ascontiguousarray(img[y0 - vy:y1 - vy, x0 - vx:x1 - vx, :3])
            ok, png = cv2.imencode(".png", crop)
            if not ok:
                raise ValueError("Resim kodlanamadı.")
            self._var("image").set(base64.b64encode(png.tobytes()).decode("ascii"))
            self._var("img_w").set(str(x1 - x0)); self._var("img_h").set(str(y1 - y0))
            self._update_image_preview()
            self.set_status(f"Resim alındı: {x1 - x0}×{y1 - y0} px", "ok", 3000)
        except Exception as e:
            self.set_status(f"Resim alınamadı: {e}", "error", 4000)
        finally:
            self.root.deiconify()

"""Canlı kayıt: fare tıklamaları, tekerlek ve tuşlar aksiyona dönüştürülür."""
import threading
import time
from ctypes import wintypes
from tkinter import messagebox

from pynput import mouse, keyboard
from pynput.keyboard import Key, KeyCode

from ..actions import _normalize
from ..core.windows import _get_window_rect
from ..core.winapi import user32, GA_ROOT, _VK_NAMES
from ..ui.theme import RED, RED_H


class RecorderMixin:
    # ================= CANLI KAYIT =================
    _REC_IGNORE = {Key.esc, Key.f6, Key.f7, Key.f8}
    _MODIFIERS = {"shift", "ctrl", "alt", "win", "lshift", "rshift", "lctrl", "rctrl", "lalt", "ralt", "altgr"}

    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            for l in (self.mouse_listener, self.rec_kb_listener):
                if l: l.stop()
            # kayıt sırasında basılı kalmış tuşları bırak aksiyonuyla kapat
            for name, info in list(self._rec_pressed.items()):
                if info["converted"]:
                    self._rec_append({"type": "Press", "key": name, "mode": "up", "hold": 0.0})
            self._rec_pressed = {}
            self.btn_rec.configure(text="🔴  Canlı Kayıt", fg_color="#3a2328", hover_color="#4a2a30", text_color=RED)
            self.update_status_pill()
            self.refresh_tree()
            self.set_status(f"Kayıt bitti · {len(self.actions)} aksiyon kaydedildi.", "ok", 4000)
            self.log(f"Kayıt bitti · {len(self.actions)} aksiyon.")
        else:
            if self.is_macro_running:
                self.set_status("Makro çalışırken kayıt başlatılamaz.", "warn", 3000)
                return
            if self.actions and not messagebox.askyesno("Canlı Kayıt", "Mevcut liste silinip yeni kayıt başlasın mı?"):
                return
            self.is_recording = True
            self.btn_rec.configure(text="⏹  Bitir (Esc)", fg_color=RED, hover_color=RED_H, text_color="white")
            self.actions = []
            self.refresh_tree()
            self.clear_selection()
            self.rec_window = self.target_window_title.get() if self.use_window_mode.get() else ""
            self.start_rec_time = time.time()
            self._rec_pressed = {}
            self._rec_lock = threading.Lock()
            self.mouse_listener = mouse.Listener(on_click=self.on_record_click, on_scroll=self.on_record_scroll)
            self.mouse_listener.start()
            self.rec_kb_listener = keyboard.Listener(on_press=self.on_record_key, on_release=self.on_record_key_up)
            self.rec_kb_listener.start()
            self.update_status_pill()
            self.set_status("Kayıt yapılıyor · tıklamalar, tuşlar ve tekerlek kaydediliyor. Bitirmek için Esc.", "warn")

    def _rec_append(self, act):
        """Kayıt listesine ekler; bekleme süresi bir önceki olaydan bu yana geçen süredir."""
        now = time.time()
        act.setdefault("delay", round(now - self.start_rec_time, 2))
        self.start_rec_time = now
        act = _normalize(act)
        self.actions.append(act)
        # başka bir olay gelirse basılı tutulan tuşlar 'bas/bırak' çiftine dönüşür
        for info in self._rec_pressed.values():
            if not info["converted"] and info["idx"] != len(self.actions) - 1:
                info["converted"] = True
                self.actions[info["idx"]]["mode"] = "down"
        self.root.after(0, self.refresh_tree)
        return len(self.actions) - 1

    def _rec_xy(self, x, y):
        if self.rec_window:
            win = _get_window_rect(self.rec_window)
            if win: x -= win.left; y -= win.top
        return int(x), int(y)

    def _own_window_at(self, x, y):
        hwnd = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        return hwnd and user32.GetAncestor(hwnd, GA_ROOT) == self._own_hwnd

    def on_record_click(self, x, y, button, pressed):
        if not pressed or not self.is_recording:
            return
        btn = {mouse.Button.left: "left", mouse.Button.right: "right", mouse.Button.middle: "middle"}.get(button)
        # programın kendi penceresine yapılan tıklamaları (örn. Bitir) kaydetme
        if not btn or self._own_window_at(x, y):
            return
        rx, ry = self._rec_xy(x, y)
        with self._rec_lock:
            self._rec_append({"type": "Click", "x": rx, "y": ry, "button": btn})

    def on_record_scroll(self, x, y, dx, dy):
        if not self.is_recording or not dy or self._own_window_at(x, y):
            return
        with self._rec_lock:
            last = self.actions[-1] if self.actions else None
            # art arda tekerlek çentiklerini tek aksiyonda birleştir
            if last and last["type"] == "Scroll" and time.time() - self.start_rec_time < 0.3 \
                    and (last["amount"] > 0) == (dy > 0):
                last["amount"] += int(dy * 120)
                self.start_rec_time = time.time()
                self.root.after(0, self.refresh_tree)
            else:
                self._rec_append({"type": "Scroll", "amount": int(dy * 120)})

    @staticmethod
    def _key_name(key):
        if isinstance(key, Key):
            n = key.name
            n = {"ctrl_l": "lctrl", "ctrl_r": "rctrl", "shift_l": "lshift", "shift_r": "rshift",
                 "alt_l": "lalt", "alt_r": "ralt", "alt_gr": "altgr", "cmd": "win", "cmd_l": "win",
                 "cmd_r": "rwin", "page_up": "pageup", "page_down": "pagedown", "caps_lock": "capslock",
                 "num_lock": "numlock", "scroll_lock": "scrolllock", "print_screen": "printscreen"}.get(n, n)
            return n if (n in _VK_NAMES) else None
        if isinstance(key, KeyCode):
            if key.char and key.char.isprintable():
                return key.char.lower()
            vk = key.vk
            if vk and (0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A):
                return chr(vk).lower()  # ctrl basılıyken char kontrol karakteri olur
            if vk and 0x60 <= vk <= 0x69:
                return f"num{vk - 0x60}"
        return None

    def on_record_key(self, key):
        if not self.is_recording:
            return False
        if key == Key.esc:
            self.root.after(0, lambda: self.is_recording and self.toggle_recording())
            return False
        if key in self._REC_IGNORE or self.is_picking:
            return
        name = self._key_name(key)
        if not name:
            return
        with self._rec_lock:
            if name in self._rec_pressed:  # otomatik tekrar
                return
            if name in self._MODIFIERS:
                idx = self._rec_append({"type": "Press", "key": name, "mode": "down", "hold": 0.0})
                self._rec_pressed[name] = {"idx": idx, "t": time.time(), "converted": True}
            else:
                idx = self._rec_append({"type": "Press", "key": name, "mode": "tap", "hold": 0.0})
                self._rec_pressed[name] = {"idx": idx, "t": time.time(), "converted": False}

    def on_record_key_up(self, key):
        if not self.is_recording:
            return False
        name = self._key_name(key)
        with self._rec_lock:
            info = self._rec_pressed.pop(name, None) if name else None
            if not info:
                return
            if info["converted"]:
                self._rec_append({"type": "Press", "key": name, "mode": "up", "hold": 0.0})
            else:
                held = time.time() - info["t"]
                if held > 0.15:
                    # uzun basış (örn. oyunda W ile yürümek) basılı tutma süresi olarak saklanır
                    self.actions[info["idx"]]["hold"] = round(held, 2)
                    self.start_rec_time = time.time()
                    self.root.after(0, self.refresh_tree)

"""Makro çalışma zamanı yardımcıları (worker thread): bekleme, tıklama, tuş, yakalama."""
import base64
import math
import random
import time

import pyautogui

from ..core.cv import np, cv2
from ..core.real_input import real_key, real_button
from ..core.screen import _screen_pixel, _window_pixel, capture_screen, capture_window
from ..core.signal_input import sig_button, _signal_click, sig_move, sig_key
from ..core.utils import _cursor_pos
from ..core.winapi import user32
from ..actions import _Stop


class RuntimeMixin:
    def _check(self):
        """Durdurulduysa _Stop fırlatır; duraklatıldıysa bekler. Bekleme süresini döndürür."""
        if not self.is_macro_running:
            raise _Stop
        if not self.is_paused:
            return 0.0
        t0 = time.perf_counter()
        while self.is_paused:
            if not self.is_macro_running:
                raise _Stop
            time.sleep(0.05)
        return time.perf_counter() - t0

    def _sleep(self, s):
        """Durdurulabilir/duraklatılabilir bekleme; duraklatmada geçen süreyi döndürür."""
        end = time.perf_counter() + max(0.0, s)
        paused = 0.0
        while True:
            p = self._check()
            end += p
            paused += p
            rem = end - time.perf_counter()
            if rem <= 0:
                return paused
            if rem > 0.003:
                time.sleep(min(rem - 0.001, 0.02))
            else:
                while time.perf_counter() < end:
                    pass
                return paused

    def _failsafe(self, ctx):
        if not ctx["hwnd"]:
            pyautogui.failSafeCheck()

    def _move_to(self, ctx, x, y):
        """Gerçek imleci hedefe götürür; İnsansı modda yumuşak bir yay çizerek."""
        if ctx["human"] and not ctx["turbo"]:
            sx, sy = _cursor_pos()
            dist = math.hypot(x - sx, y - sy)
            if dist > 3:
                steps = max(6, min(30, int(dist / 25)))
                dur = random.uniform(0.06, 0.16) + min(dist, 1500) / 9000
                bend = random.uniform(-0.12, 0.12) * dist
                nx, ny = -(y - sy) / dist, (x - sx) / dist
                for i in range(1, steps + 1):
                    t = i / steps
                    e = t * t * (3 - 2 * t)
                    arc = math.sin(math.pi * t) * bend
                    user32.SetCursorPos(int(sx + (x - sx) * e + nx * arc), int(sy + (y - sy) * e + ny * arc))
                    self._sleep(dur / steps)
        user32.SetCursorPos(int(x), int(y))

    def _jitter(self, ctx, x, y):
        if ctx["human"] and not ctx["turbo"]:
            return x + random.randint(-2, 2), y + random.randint(-2, 2)
        return x, y

    def _hold(self, item):
        self._held.add(item)

    def _release(self, item):
        self._held.discard(item)

    def _release_all(self):
        for item in list(self._held):
            try:
                kind = item[0]
                if kind == "rk": real_key(item[1], True)
                elif kind == "rm": real_button(item[1], True)
                elif kind == "sk": sig_key(item[1], item[2], True)
                elif kind == "sm": sig_button(item[1], item[2], item[3], item[4], True)
            except Exception:
                pass
        self._held.clear()

    def _click(self, ctx, x, y, button="left", double=False, hold=0.0, here=False):
        hwnd = ctx["hwnd"]
        if hwnd:
            if hold > 0:
                item = ("sm", hwnd, x, y, button)
                sig_button(hwnd, x, y, button, False); self._hold(item)
                self._sleep(hold)
                sig_button(hwnd, x, y, button, True); self._release(item)
            else:
                _signal_click(hwnd, x, y, button, double)
            return
        if not here:
            self._move_to(ctx, x, y)
        self._failsafe(ctx)
        for n in range(2 if double else 1):
            real_button(button, False); self._hold(("rm", button))
            self._sleep(hold if hold > 0 else (0.0 if ctx["turbo"] else random.uniform(0.02, 0.05) if ctx["human"] else 0.01))
            real_button(button, True); self._release(("rm", button))
            if double and n == 0:
                self._sleep(0.06)

    def _keys(self, ctx, vks, up):
        hwnd = ctx["hwnd"]
        for vk in (reversed(vks) if up else vks):
            item = ("sk", hwnd, vk) if hwnd else ("rk", vk)
            if hwnd: sig_key(hwnd, vk, up)
            else: real_key(vk, up)
            if up: self._release(item)
            else: self._hold(item)

    def _found_click(self, ctx, x, y, mode):
        if mode == "none":
            return
        if mode == "move":
            if ctx["hwnd"]: sig_move(ctx["hwnd"], x, y)
            else: self._move_to(ctx, x, y)
            return
        self._click(ctx, x, y, button="right" if mode == "right" else "left", double=(mode == "double"))

    def _capture(self, ctx):
        if ctx["hwnd"]:
            return capture_window(ctx["hwnd"])
        return capture_screen()

    def _pixel_matches(self, ctx, x, y, rgb, tol):
        px = _window_pixel(ctx["hwnd"], x, y) if ctx["hwnd"] else _screen_pixel(x, y)
        return bool(px) and all(abs(a - b) <= tol for a, b in zip(px, rgb))

    def _template(self, data):
        t = self._tmpl_cache.get(data)
        if t is None:
            arr = np.frombuffer(base64.b64decode(data), dtype=np.uint8)
            t = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if t is None:
                raise ValueError("Resim çözülemedi")
            self._tmpl_cache[data] = t
        return t

"""F7 hızlı tıklayıcı ve CPS ayarı."""
import random
import threading
import time

import pyautogui

from ..core.real_input import _turbo_click
from ..core.signal_input import _signal_click
from ..core.utils import _precise_sleep
from ..core.windows import _find_window
from ..ui.theme import _cps_to_slider, _slider_to_cps


class ClickerMixin:
    # ================= HIZ =================
    def on_cps_slide(self, v):
        self.f7_cps = float(_slider_to_cps(v))
        self.cps_text.set(str(int(self.f7_cps)))

    def on_cps_entry(self):
        try:
            cps = float(self.cps_text.get().replace(",", "."))
        except ValueError:
            cps = self.f7_cps
        self.set_cps(cps)

    def set_cps(self, cps):
        self.f7_cps = float(max(1, min(1000, round(cps))))
        self.cps_text.set(str(int(self.f7_cps)))
        self.cps_slider.set(_cps_to_slider(self.f7_cps))

    # ================= HIZLI TIKLAYICI =================
    def toggle_f7_clicker(self):
        if self.is_f7_running:
            self.is_f7_running = False
            self._set_f7_ui(False)
        else:
            self.on_cps_entry()
            self.is_f7_running = True
            self._sync_f7_settings()
            if self.use_window_mode.get() and not self._f7_hwnd:
                self.is_f7_running = False
                self.set_status("Pencere modu açık ama hedef pencere bulunamadı.", "error", 4000)
                return
            self._set_f7_ui(True)
            threading.Thread(target=self.run_f7, daemon=True).start()

    def _sync_f7_settings(self):
        # F7 çalışırken hız/mod değişikliklerini thread'e aktar (Tk main thread'de okunur)
        if not self.is_f7_running: return
        self._f7_interval = 1.0 / max(self.f7_cps, 1.0)
        self._f7_turbo = self.use_turbo_mode.get()
        self._f7_human = self.human_speed.get()
        self._f7_hwnd = None
        self._f7_window_mode = self.use_window_mode.get()
        if self._f7_window_mode:
            # Pencere modunda F7, editördeki X/Y noktasına sinyal tıklaması gönderir
            self._f7_hwnd = _find_window(self.target_window_title.get())
            try:
                self._f7_pos = (int(self._var("x", "int", 0).get()), int(self._var("y", "int", 0).get()))
            except ValueError:
                pass
        self.root.after(100, self._sync_f7_settings)

    def run_f7(self):
        next_t = time.perf_counter()
        while self.is_f7_running:
            try:
                hwnd = self._f7_hwnd
                if hwnd:
                    _signal_click(hwnd, *self._f7_pos)
                elif self._f7_window_mode:
                    pass  # hedef pencere kapandı; gerçek fareye düşme
                else:
                    pyautogui.failSafeCheck()
                    _turbo_click()
            except pyautogui.FailSafeException:
                self.is_f7_running = False
                self.root.after(0, lambda: (self._set_f7_ui(False),
                                            self.set_status("Güvenlik durdurması: fare ekran köşesine götürüldü.", "error", 5000)))
                break
            except Exception:
                pass

            interval = self._f7_interval
            if self._f7_human and not self._f7_turbo:
                interval *= random.uniform(0.9, 1.1)
            next_t += interval
            now = time.perf_counter()
            if next_t < now:
                # geride kaldıysak toplu tıklama yapma, zamanlamayı sıfırla
                next_t = now
            else:
                _precise_sleep(next_t - now)

"""Makroyu başlatma/durdurma/duraklatma ve ana çalışma döngüsü."""
import math
import random
import threading
import time

import pyautogui

from ..actions import _Stop
from ..core.utils import _delay_value
from ..core.windows import _find_window
from ..ui.theme import SURFACE2, TEXT, AMBER


class RunnerMixin:
    # ================= MAKRO =================
    def toggle_macro(self):
        if self.is_macro_running:
            self.is_macro_running = False
            self.is_paused = False
            self._set_play_button(False)
            self.update_status_pill()
        else:
            self.start_macro_thread()

    def toggle_pause(self):
        if not self.is_macro_running:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.configure(text="▶  Devam", fg_color=AMBER, text_color="#1f1606")
            self.log("Duraklatıldı.")
        else:
            self.btn_pause.configure(text="❚❚  Duraklat", fg_color=SURFACE2, text_color=TEXT)
            self.log("Devam ediliyor.")
        self.update_status_pill()

    def _validate_flow(self, actions):
        labels = [a["name"] for a in actions if a["type"] == "Label" and a.get("enabled", True)]
        dup = {n for n in labels if labels.count(n) > 1}
        if dup:
            return f"Aynı adlı birden fazla etiket var: {', '.join(dup)}"
        for i, a in enumerate(actions):
            if not a.get("enabled", True):
                continue
            refs = []
            if a["type"] == "Goto": refs.append(a.get("label"))
            for k in ("on_timeout", "on_true", "on_false", "on_found", "on_missing"):
                v = a.get(k)
                if isinstance(v, str) and v.startswith("goto:"): refs.append(v[5:])
            for r in refs:
                if r not in labels:
                    return f"#{i + 1}: “{r}” etiketi yok (silinmiş ya da devre dışı)."
        return None

    def start_macro_thread(self):
        if self.is_macro_running: return
        if not self.actions:
            self.set_status("Çalıştırmak için önce aksiyon ekle.", "warn", 3000)
            return
        if self.is_recording:
            self.set_status("Kayıt sürerken makro başlatılamaz.", "warn", 3000)
            return

        def num(var, cast, default=0):
            try:
                return max(0, cast(str(var.get()).replace(",", ".") or default))
            except ValueError:
                var.set(str(default))
                return default
        if self.use_window_mode.get() and not self.target_window_title.get():
            self.set_status("Pencere modu açık ama hedef pencere seçilmedi.", "error", 4000)
            return
        actions = [dict(a) for a in self.actions]
        err = self._validate_flow(actions)
        if err:
            self.set_status(err, "error", 6000)
            return
        # Tk değişkenleri worker thread'den okunmasın diye ayarlar burada alınır
        cfg = {
            "loops": num(self.loop_var, int),
            "limit": num(self.limit_var, float),
            "start_delay": num(self.start_delay_var, float),
            "window": self.use_window_mode.get(),
            "title": self.target_window_title.get(),
            "turbo": self.use_turbo_mode.get(),
            "human": self.human_speed.get(),
        }
        self.is_macro_running = True
        self.is_paused = False
        self._cur_idx = None
        self._run_info = {"loops": cfg["loops"]}
        self._set_play_button(True)
        self.update_status_pill()
        self.tabs.set("Aksiyonlar")
        threading.Thread(target=self.run_macro, args=(cfg, actions), daemon=True).start()

    def run_macro(self, cfg, actions):
        loops = cfg["loops"]
        ctx = {"hwnd": None, "turbo": cfg["turbo"], "human": cfg["human"]}
        labels = {a["name"]: i for i, a in enumerate(actions) if a["type"] == "Label" and a.get("enabled", True)}
        cnt = 0
        error = None
        reason = None
        self._tmpl_cache = {}
        try:
            # geri sayım: oyuna/pencereye geçmek için zaman tanır
            remaining = cfg["start_delay"]
            while remaining > 0:
                self._run_info["countdown"] = math.ceil(remaining)
                step = min(remaining, 0.1)
                self._sleep(step)
                remaining -= step
            self._run_info["countdown"] = 0
            start = time.time()
            self._run_info["start"] = start
            t_end = start + cfg["limit"] * 60 if cfg["limit"] else None
            self.log(f"Makro başladı · {len(actions)} aksiyon · "
                     f"{'pencere modu: ' + cfg['title'] if cfg['window'] else 'gerçek giriş'}")

            while self.is_macro_running and (loops == 0 or cnt < loops):
                if cfg["window"]:
                    # Pencere modu: odak çalınmaz, fare/klavye kullanılmaz, her şey mesajla gider
                    ctx["hwnd"] = _find_window(cfg["title"])
                    if not ctx["hwnd"]:
                        error = f"Pencere bulunamadı: {cfg['title']}"
                        break
                self._run_info["loop"] = cnt + 1
                goto_counts = {}
                pc = 0
                steps_without_wait = 0
                while pc < len(actions):
                    self._check()
                    if t_end and time.time() >= t_end:
                        reason = f"Süre sınırı ({cfg['limit']:g} dk) doldu."
                        raise _Stop
                    a = actions[pc]
                    self._cur_idx = pc
                    self._run_info["pc"] = pc
                    if not a.get("enabled", True) or a["type"] == "Label":
                        pc += 1
                        continue
                    if a["type"] == "Goto":
                        target = a.get("label")
                        times = int(a.get("times", 0))
                        c = goto_counts.get(pc, 0)
                        if times == 0 or c < times:
                            goto_counts[pc] = c + 1
                            pc = labels[target]
                        else:
                            goto_counts[pc] = 0  # iç içe döngüler için sayaç sıfırlanır
                            pc += 1
                        # beklemesiz sonsuz döngü arayüzü kilitlemesin
                        steps_without_wait += 1
                        if steps_without_wait > 1000:
                            time.sleep(0.001); steps_without_wait = 0
                        continue

                    d = _delay_value(a.get("delay", 0))
                    if d > 0:
                        if cfg["human"] and not cfg["turbo"] and not isinstance(a.get("delay"), str):
                            d *= random.uniform(0.85, 1.15)
                        self._sleep(d)
                        steps_without_wait = 0

                    try:
                        out = self._exec(pc, a, ctx)
                    except (_Stop, pyautogui.FailSafeException):
                        raise
                    except Exception as e:
                        self.log(f"#{pc + 1} hata: {e}")
                        out = "next"

                    if out == "stop":
                        reason = f"#{pc + 1} makroyu durdurdu."
                        raise _Stop
                    if isinstance(out, str) and out.startswith("goto:"):
                        pc = labels[out[5:]]
                    else:
                        pc += 1
                    steps_without_wait += 1
                    if steps_without_wait > 1000:
                        time.sleep(0.001); steps_without_wait = 0
                cnt += 1
        except _Stop:
            pass
        except pyautogui.FailSafeException:
            error = "Güvenlik durdurması: fare ekran köşesine götürüldü."
        except Exception as e:
            error = f"Beklenmeyen hata: {e}"
        finally:
            self._release_all()
            self.is_macro_running = False
            self.is_paused = False
            self._cur_idx = None

        if error:
            self.log(error)
        elif reason:
            self.log(reason)
        self.log(f"Makro bitti · {cnt} tur tamamlandı.")

        def done():
            self._set_play_button(False)
            self.update_status_pill()
            if error:
                self.set_status(error, "error", 8000)
            else:
                self.set_status(f"Makro durdu · {cnt} tur tamamlandı." + (f"  {reason}" if reason else ""), "ok", 6000)
        self.root.after(0, done)

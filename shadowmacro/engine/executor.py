"""Tek bir aksiyonu tipine göre çalıştıran yürütücü."""
import random
import time
import winsound

from ..actions import _outcome_text
from ..core.cv import HAS_CV
from ..core.real_input import real_button, real_move_rel, real_scroll, real_type_char
from ..core.screen import find_template, find_color
from ..core.signal_input import _SIG_BTN, sig_button, sig_move, sig_char, sig_scroll
from ..core.utils import _parse_keys, _parse_rgb
from ..core.windows import _focus_target
from ..core.winapi import user32


class ExecutorMixin:
    def _exec(self, i, a, ctx):
        """Bir aksiyonu çalıştırır; sonucu döndürür: 'next', 'stop' ya da 'goto:etiket'."""
        t = a["type"]
        n = f"#{i + 1}"
        if t == "Click":
            x, y = self._jitter(ctx, a["x"], a["y"])
            self._click(ctx, x, y, a.get("button", "left"), a.get("double", False), float(a.get("hold", 0)),
                        a.get("here", False) and not ctx["hwnd"])
        elif t == "Move":
            if a.get("relative"):
                if not ctx["hwnd"]:
                    self._failsafe(ctx)
                    real_move_rel(a["x"], a["y"])
            elif ctx["hwnd"]:
                sig_move(ctx["hwnd"], a["x"], a["y"])
            else:
                self._move_to(ctx, a["x"], a["y"])
        elif t == "Drag":
            btn, dur = a.get("button", "left"), max(0.0, float(a.get("duration", 0.3)))
            x1, y1, x2, y2 = a["x"], a["y"], a["x2"], a["y2"]
            steps = max(5, int(dur * 60))
            hwnd = ctx["hwnd"]
            if hwnd:
                item = ("sm", hwnd, x2, y2, btn)
                sig_button(hwnd, x1, y1, btn, False); self._hold(item)
                for s in range(1, steps + 1):
                    sig_move(hwnd, x1 + (x2 - x1) * s / steps, y1 + (y2 - y1) * s / steps, _SIG_BTN[btn][3])
                    self._sleep(dur / steps)
                sig_button(hwnd, x2, y2, btn, True); self._release(item)
            else:
                self._move_to(ctx, x1, y1)
                self._failsafe(ctx)
                real_button(btn, False); self._hold(("rm", btn))
                self._sleep(0.05)
                for s in range(1, steps + 1):
                    user32.SetCursorPos(int(x1 + (x2 - x1) * s / steps), int(y1 + (y2 - y1) * s / steps))
                    self._sleep(dur / steps)
                self._sleep(0.05)
                real_button(btn, True); self._release(("rm", btn))
        elif t == "Press":
            vks = _parse_keys(a["key"])
            mode = a.get("mode", "tap")
            if not ctx["hwnd"]:
                self._failsafe(ctx)
            if mode in ("tap", "down"):
                self._keys(ctx, vks, False)
            if mode == "tap":
                hold = float(a.get("hold", 0))
                # oyunlar girişi kare başına okur; 0 ms'lik basış kaçabilir
                self._sleep(hold if hold > 0 else (0.0 if ctx["turbo"] else
                                                   random.uniform(0.03, 0.07) if ctx["human"] else 0.03))
            if mode in ("tap", "up"):
                self._keys(ctx, vks, True)
        elif t == "Type":
            text = a.get("text", "").replace("\\n", "\n")
            iv = float(a.get("interval", 0.02))
            target = _focus_target(ctx["hwnd"]) if ctx["hwnd"] else None
            for ch in text:
                self._check()
                if ctx["hwnd"]: sig_char(ctx["hwnd"], ch, target)
                else: real_type_char(ch)
                self._sleep(iv * random.uniform(0.5, 1.6) if ctx["human"] and not ctx["turbo"] else iv)
        elif t == "Scroll":
            if ctx["hwnd"]: sig_scroll(ctx["hwnd"], a["amount"])
            else:
                self._failsafe(ctx)
                real_scroll(a["amount"])
        elif t == "Wait":
            pass  # bekleme, aksiyonun "delay" alanıyla zaten yapıldı
        elif t == "WaitColor":
            rgb, tol = _parse_rgb(a["color"]), int(a.get("tolerance", 10))
            want = a.get("until", "appear") == "appear"
            deadline = time.perf_counter() + float(a.get("timeout", 5))
            while True:
                if self._pixel_matches(ctx, a["x"], a["y"], rgb, tol) == want:
                    return "next"
                if time.perf_counter() >= deadline:
                    self.log(f"{n} Renk Bekle: zaman aşıldı · {_outcome_text(a.get('on_timeout', 'next'))}")
                    return a.get("on_timeout", "next")
                deadline += self._check()
                deadline += self._sleep(0.05)
        elif t == "IfColor":
            ok = self._pixel_matches(ctx, a["x"], a["y"], _parse_rgb(a["color"]), int(a.get("tolerance", 10)))
            out = a.get("on_true" if ok else "on_false", "next")
            self.log(f"{n} Renk Kontrol: {'eşleşti' if ok else 'eşleşmedi'} · {_outcome_text(out)}")
            return out
        elif t in ("FindImage", "FindColor"):
            if not HAS_CV:
                self.log(f"{n} opencv-python/numpy kurulu değil, atlandı.")
                return "next"
            if t == "FindImage":
                tmpl, conf = self._template(a["image"]), float(a.get("confidence", 0.85))
            else:
                rgb, tol = _parse_rgb(a["color"]), int(a.get("tolerance", 10))
            deadline = time.perf_counter() + float(a.get("timeout", 0))
            name = "Resim" if t == "FindImage" else "Renk"
            while True:
                img, ox, oy = self._capture(ctx)
                hit = None
                if img is not None:
                    if t == "FindImage":
                        r = find_template(img, tmpl, conf)
                        if r: hit = (r[0], r[1], f" (benzerlik {r[2]:.2f})")
                    else:
                        r = find_color(img, rgb, tol)
                        if r: hit = (r[0], r[1], "")
                if hit:
                    x, y = hit[0] + ox, hit[1] + oy
                    self.log(f"{n} {name} bulundu @ {x}, {y}{hit[2]}")
                    self._found_click(ctx, x, y, a.get("click", "left"))
                    return a.get("on_found", "next")
                if time.perf_counter() >= deadline:
                    self.log(f"{n} {name} bulunamadı · {_outcome_text(a.get('on_missing', 'next'))}")
                    return a.get("on_missing", "next")
                deadline += self._check()
                deadline += self._sleep(0.1)
        elif t == "Notify":
            msg = a.get("text") or "Bildirim"
            self.log(f"{n} 🔔 {msg}")
            self.root.after(0, lambda m=msg: self.set_status(f"🔔 {m}", "warn", 10000))
            if a.get("beep", True):
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            if a.get("stop"):
                return "stop"
        return "next"

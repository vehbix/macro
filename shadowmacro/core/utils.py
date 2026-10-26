"""Genel yardımcılar: zamanlama, imleç, tuş/bekleme/renk ayrıştırma."""
import ctypes
import random
import time
from ctypes import wintypes

from .winapi import user32, VK_SHIFT, _VK_NAMES


def _precise_sleep(seconds):
    """time.sleep tek başına ~1-15 ms sapar; yüksek CPS için son kısmı spin ile bekler."""
    end = time.perf_counter() + seconds
    if seconds > 0.002:
        time.sleep(seconds - 0.002)
    while time.perf_counter() < end:
        pass


def _cursor_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def _parse_keys(spec):
    """'ctrl+shift+s' -> [vk, ...]. Bilinmeyen tuşta ValueError."""
    spec = spec.strip().lower()
    parts = [p for p in spec.split("+") if p] or (["+"] if "+" in spec else [])
    if not parts:
        raise ValueError("Tuş boş")
    vks = []
    for part in parts:
        vk = _VK_NAMES.get(part)
        if vk is None and len(part) == 1:
            res = user32.VkKeyScanW(part)
            if res != -1:
                if res & 0x100 and VK_SHIFT not in vks:
                    vks.append(VK_SHIFT)
                vk = res & 0xFF
        if vk is None:
            raise ValueError(f"Bilinmeyen tuş: {part}")
        vks.append(vk)
    return vks


def _parse_delay(text):
    """'0.5' -> 0.5, '1-3' -> '1-3' (rastgele aralık). Hatalıysa ValueError."""
    s = str(text).strip().replace(",", ".")
    if not s:
        return 0.0
    if "-" in s[1:]:
        a, b = s.split("-", 1)
        a, b = float(a), float(b)
        if a < 0 or b < a:
            raise ValueError
        return f"{a:g}-{b:g}"
    v = float(s)
    if v < 0:
        raise ValueError
    return v


def _delay_value(d):
    if isinstance(d, str) and "-" in d[1:]:
        a, b = d.split("-", 1)
        return random.uniform(float(a), float(b))
    return float(d or 0)


def _fmt_delay(d):
    if isinstance(d, str):
        return d.replace("-", "–") + " sn"
    return f"{float(d or 0):g} sn"

def _parse_rgb(text):
    rgb = [int(c) for c in str(text).replace(" ", "").split(",")]
    if len(rgb) != 3 or not all(0 <= c <= 255 for c in rgb):
        raise ValueError
    return tuple(rgb)

"""Pencere listeleme, bulma ve hedef (çocuk) pencere çözümleme."""
import ctypes
from ctypes import wintypes

from .winapi import user32, HWND, GUITHREADINFO, CWP_SKIP

_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [_EnumWindowsProc, wintypes.LPARAM]


def _get_all_windows():
    titles = []

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                if buf.value.strip():
                    titles.append(buf.value)
        return True

    user32.EnumWindows(_EnumWindowsProc(cb), 0)
    return list(dict.fromkeys(titles))


def _find_window(title):
    return user32.FindWindowW(None, title) or None


class _WinRect:
    def __init__(self, left, top, right=0, bottom=0):
        self.left = left
        self.top = top
        self.width = right - left
        self.height = bottom - top


def _hwnd_rect(hwnd):
    r = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return _WinRect(r.left, r.top, r.right, r.bottom)


def _get_window_rect(title):
    hwnd = _find_window(title)
    return _hwnd_rect(hwnd) if hwnd else None


def _make_lparam(x, y):
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


def _target_at(hwnd, sx, sy):
    """Ekran noktasının altındaki en derin çocuk pencereyi ve o pencereye göre
    istemci koordinatını döndürür (tarayıcı, oyun başlatıcı vb. çocuk pencereli
    uygulamalar mesajı ana pencerede değil çocukta bekler)."""
    while True:
        pt = wintypes.POINT(int(sx), int(sy))
        user32.ScreenToClient(hwnd, ctypes.byref(pt))
        child = user32.ChildWindowFromPointEx(hwnd, pt, CWP_SKIP)
        if not child or child == hwnd:
            return hwnd, pt.x, pt.y
        hwnd = child


def _focus_target(hwnd):
    """Klavye mesajları pencerenin içindeki odaklı kontrole gitmeli (ör. metin kutusu)."""
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    if not tid:
        return hwnd
    info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
    if user32.GetGUIThreadInfo(tid, ctypes.byref(info)) and info.hwndFocus:
        focus = info.hwndFocus
        if focus == hwnd or user32.IsChild(hwnd, focus):
            return focus
    # Arka plandaki pencerede odaklı kontrol yoktur (Windows odağı pencere öne
    # gelince geri verir). Pencerenin ortasındaki kontrolü hedef alıyoruz: oyunda
    # ana pencere, tarayıcıda içerik alanı, basit formlarda metin kutusu.
    rect = _hwnd_rect(hwnd)
    if rect:
        return _target_at(hwnd, rect.left + rect.width // 2, rect.top + rect.height // 2)[0]
    return hwnd

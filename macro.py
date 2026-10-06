import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import ctypes
from ctypes import wintypes
import base64
import json
import math
import os
import queue
import random
import sys
import threading
import time
import winsound
import pyautogui
from pynput import mouse, keyboard
from pynput.keyboard import Key, KeyCode

try:
    import numpy as np
    import cv2
    HAS_CV = True
except ImportError:
    HAS_CV = False

if sys.platform != "win32":
    raise SystemExit("ShadowMacro V12 sadece Windows'ta çalışır.")

# --- GÜVENLİK ---
# Fare ekranın bir köşesine götürülürse gerçek girişli makro/tıklayıcı durur.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ============================================================================
#  WIN32
# ============================================================================
# pynput/pyautogui ctypes.windll üzerindeki fonksiyonlara kendi argtypes'larını
# atıyor; çakışmasın diye kendi DLL nesnelerimizi kullanıyoruz.
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32")
winmm = ctypes.WinDLL("winmm")

HWND = wintypes.HWND
HDC = wintypes.HDC

user32.FindWindowW.restype = HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.ChildWindowFromPointEx.restype = HWND
user32.ChildWindowFromPointEx.argtypes = [HWND, wintypes.POINT, wintypes.UINT]
user32.WindowFromPoint.restype = HWND
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.GetAncestor.restype = HWND
user32.GetAncestor.argtypes = [HWND, wintypes.UINT]
user32.ScreenToClient.argtypes = [HWND, ctypes.POINTER(wintypes.POINT)]
user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.PostMessageW.argtypes = [HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetDC.restype = HDC
user32.GetDC.argtypes = [HWND]
user32.ReleaseDC.argtypes = [HWND, HDC]
user32.PrintWindow.argtypes = [HWND, HDC, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.VkKeyScanW.restype = ctypes.c_short
user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsChild.argtypes = [HWND, HWND]
user32.IsWindowVisible.argtypes = [HWND]
user32.GetWindowTextLengthW.argtypes = [HWND]
user32.GetWindowTextW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]

gdi32.CreateCompatibleDC.restype = HDC
gdi32.CreateCompatibleDC.argtypes = [HDC]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.CreateCompatibleBitmap.argtypes = [HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [HDC, wintypes.HGDIOBJ]
gdi32.GetPixel.restype = wintypes.DWORD
gdi32.GetPixel.argtypes = [HDC, ctypes.c_int, ctypes.c_int]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [HDC]
gdi32.BitBlt.argtypes = [HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]

WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102
WM_MOUSEMOVE, WM_MOUSEWHEEL = 0x0200, 0x020A
CWP_SKIP = 0x0001 | 0x0002 | 0x0004  # görünmez / pasif / şeffaf çocukları atla
PW_RENDERFULLCONTENT = 0x00000002
GA_ROOT = 2
SRCCOPY, CAPTUREBLT = 0x00CC0020, 0x40000000

# --- SendInput ---
INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE, KEYEVENTF_SCANCODE = 0x1, 0x2, 0x4, 0x8
MOUSEEVENTF_MOVE, MOUSEEVENTF_WHEEL = 0x0001, 0x0800


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.SendInput.restype = wintypes.UINT
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD), ("hwndActive", HWND),
                ("hwndFocus", HWND), ("hwndCapture", HWND), ("hwndMenuOwner", HWND),
                ("hwndMoveSize", HWND), ("hwndCaret", HWND), ("rcCaret", wintypes.RECT)]


user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


gdi32.GetDIBits.argtypes = [HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
                            ctypes.POINTER(BITMAPINFO), wintypes.UINT]

VK_SHIFT = 0x10
VK_RETURN = 0x0D
_VK_NAMES = {
    "enter": 0x0D, "return": 0x0D, "tab": 0x09, "space": 0x20, "spacebar": 0x20,
    "esc": 0x1B, "escape": 0x1B, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "insert": 0x2D, "ins": 0x2D, "home": 0x24, "end": 0x23, "pageup": 0x21, "pgup": 0x21,
    "pagedown": 0x22, "pgdn": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "shift": 0x10, "lshift": 0xA0, "rshift": 0xA1,
    "ctrl": 0x11, "control": 0x11, "lctrl": 0xA2, "rctrl": 0xA3,
    "alt": 0x12, "lalt": 0xA4, "ralt": 0xA5, "altgr": 0xA5,
    "win": 0x5B, "lwin": 0x5B, "rwin": 0x5C, "apps": 0x5D, "menu": 0x5D,
    "capslock": 0x14, "numlock": 0x90, "scrolllock": 0x91, "pause": 0x13,
    "printscreen": 0x2C, "prtsc": 0x2C,
    **{f"f{i}": 0x6F + i for i in range(1, 25)},
    **{f"num{i}": 0x60 + i for i in range(10)},
    "num*": 0x6A, "num+": 0x6B, "num-": 0x6D, "num.": 0x6E, "num/": 0x6F,
}
# Genişletilmiş tuşlar: scancode'la gönderilirken E0 öneki gerekir
_EXTENDED = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E,
             0x5B, 0x5C, 0x5D, 0x6F, 0x90, 0xA3, 0xA5, 0x2C}


# ---------------------------------------------------------------------------
#  Genel yardımcılar
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
#  Pencereler
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
#  GERÇEK GİRİŞ (SendInput, scancode — DirectInput oyunları da algılar)
# ---------------------------------------------------------------------------
_MOUSE_FLAGS = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010), "middle": (0x0020, 0x0040)}


def _send(*inputs):
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def _mi(flags, dx=0, dy=0, data=0):
    i = INPUT(type=INPUT_MOUSE)
    i.u.mi = MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)
    return i


def _ki(vk, scan, flags):
    i = INPUT(type=INPUT_KEYBOARD)
    i.u.ki = KEYBDINPUT(vk, scan, flags, 0, 0)
    return i


def real_key(vk, up):
    scan = user32.MapVirtualKeyW(vk, 0)
    flags = KEYEVENTF_KEYUP if up else 0
    if scan:
        flags |= KEYEVENTF_SCANCODE
        if vk in _EXTENDED:
            flags |= KEYEVENTF_EXTENDEDKEY
    _send(_ki(vk, scan, flags))


def real_button(button, up):
    _send(_mi(_MOUSE_FLAGS[button][1 if up else 0]))


def real_move_rel(dx, dy):
    _send(_mi(MOUSEEVENTF_MOVE, int(dx), int(dy)))


def real_scroll(amount):
    _send(_mi(MOUSEEVENTF_WHEEL, data=int(amount)))


def real_type_char(ch):
    if ch == "\n":
        real_key(VK_RETURN, False); real_key(VK_RETURN, True)
        return
    data = ch.encode("utf-16-le")
    for i in range(0, len(data), 2):
        unit = int.from_bytes(data[i:i + 2], "little")
        _send(_ki(0, unit, KEYEVENTF_UNICODE), _ki(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))


def _turbo_click(tx=None, ty=None):
    if tx is not None and ty is not None:
        user32.SetCursorPos(int(tx), int(ty))
    _send(_mi(_MOUSE_FLAGS["left"][0]), _mi(_MOUSE_FLAGS["left"][1]))


# ---------------------------------------------------------------------------
#  PENCERE SİNYALLERİ (gerçek fare/klavye kullanılmaz)
#  Koordinatlar pencerenin sol-üst köşesine (GetWindowRect) göredir.
# ---------------------------------------------------------------------------
_SIG_BTN = {  # down, up, dblclk, MK_ bayrağı
    "left": (0x0201, 0x0202, 0x0203, 0x0001),
    "right": (0x0204, 0x0205, 0x0206, 0x0002),
    "middle": (0x0207, 0x0208, 0x0209, 0x0010),
}


def _sig_point(hwnd, wx, wy):
    rect = _hwnd_rect(hwnd)
    if not rect:
        return None
    return _target_at(hwnd, rect.left + wx, rect.top + wy)


def sig_button(hwnd, wx, wy, button, up):
    p = _sig_point(hwnd, wx, wy)
    if not p:
        return
    target, cx, cy = p
    down_msg, up_msg, _, mk = _SIG_BTN[button]
    lp = _make_lparam(cx, cy)
    if up:
        user32.PostMessageW(target, up_msg, 0, lp)
    else:
        user32.PostMessageW(target, WM_MOUSEMOVE, 0, lp)
        user32.PostMessageW(target, down_msg, mk, lp)


def _signal_click(hwnd, wx, wy, button="left", double=False):
    p = _sig_point(hwnd, wx, wy)
    if not p:
        return
    target, cx, cy = p
    down_msg, up_msg, dbl_msg, mk = _SIG_BTN[button]
    lp = _make_lparam(cx, cy)
    user32.PostMessageW(target, WM_MOUSEMOVE, 0, lp)
    user32.PostMessageW(target, down_msg, mk, lp)
    user32.PostMessageW(target, up_msg, 0, lp)
    if double:
        user32.PostMessageW(target, dbl_msg, mk, lp)
        user32.PostMessageW(target, up_msg, 0, lp)


def sig_move(hwnd, wx, wy, mk=0):
    p = _sig_point(hwnd, wx, wy)
    if p:
        user32.PostMessageW(p[0], WM_MOUSEMOVE, mk, _make_lparam(p[1], p[2]))


def sig_key(hwnd, vk, up):
    target = _focus_target(hwnd)
    scan = user32.MapVirtualKeyW(vk, 0)
    lp = 1 | (scan << 16) | ((1 << 24) if vk in _EXTENDED else 0)
    if up:
        lp |= (1 << 30) | (1 << 31)
    user32.PostMessageW(target, WM_KEYUP if up else WM_KEYDOWN, vk, lp)


def sig_char(hwnd, ch, target=None):
    target = target or _focus_target(hwnd)
    if ch == "\n":
        sig_key(hwnd, VK_RETURN, False); sig_key(hwnd, VK_RETURN, True)
        return
    data = ch.encode("utf-16-le")
    for i in range(0, len(data), 2):
        user32.PostMessageW(target, WM_CHAR, int.from_bytes(data[i:i + 2], "little"), 1)


def sig_scroll(hwnd, amount):
    rect = _hwnd_rect(hwnd)
    if not rect:
        return
    sx, sy = rect.left + rect.width // 2, rect.top + rect.height // 2
    target, _, _ = _target_at(hwnd, sx, sy)
    user32.PostMessageW(target, WM_MOUSEWHEEL, (int(amount) & 0xFFFF) << 16, _make_lparam(sx, sy))


# ---------------------------------------------------------------------------
#  EKRAN OKUMA
# ---------------------------------------------------------------------------
def _screen_pixel(x, y):
    dc = user32.GetDC(None)
    try:
        c = gdi32.GetPixel(dc, int(x), int(y))
    finally:
        user32.ReleaseDC(None, dc)
    if c == 0xFFFFFFFF:
        return None
    return c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF


def _window_pixel(hwnd, wx, wy):
    """Pencerenin pikselini PrintWindow ile okur; pencere başka bir pencerenin
    arkasında kalsa bile çalışır (simge durumunda değilse)."""
    rect = _hwnd_rect(hwnd)
    if not rect or not (0 <= wx < rect.width and 0 <= wy < rect.height):
        return None
    screen_dc = user32.GetDC(None)
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)
    bmp = gdi32.CreateCompatibleBitmap(screen_dc, rect.width, rect.height)
    old = gdi32.SelectObject(mem_dc, bmp)
    try:
        if not user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT):
            return None
        c = gdi32.GetPixel(mem_dc, int(wx), int(wy))
        if c == 0xFFFFFFFF:
            return None
        return c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF
    finally:
        gdi32.SelectObject(mem_dc, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(None, screen_dc)


def _grab(w, h, draw):
    """draw(mem_dc, screen_dc) ile çizilen w×h görüntüyü BGRA numpy dizisi olarak döndürür."""
    if w <= 0 or h <= 0:
        return None
    screen_dc = user32.GetDC(None)
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)
    bmp = gdi32.CreateCompatibleBitmap(screen_dc, w, h)
    old = gdi32.SelectObject(mem_dc, bmp)
    try:
        ok = draw(mem_dc, screen_dc)
        gdi32.SelectObject(mem_dc, old)
        if not ok:
            return None
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h  # yukarıdan aşağı
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        buf = ctypes.create_string_buffer(w * h * 4)
        if not gdi32.GetDIBits(mem_dc, bmp, 0, h, buf, ctypes.byref(bmi), 0):
            return None
        return np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4).copy()
    finally:
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(None, screen_dc)


def capture_screen():
    """Tüm monitörleri kapsayan görüntü + sol-üst köşenin ekran koordinatı."""
    vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    vw, vh = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
    img = _grab(vw, vh, lambda mem, scr: gdi32.BitBlt(mem, 0, 0, vw, vh, scr, vx, vy, SRCCOPY | CAPTUREBLT))
    return img, vx, vy


def capture_window(hwnd):
    rect = _hwnd_rect(hwnd)
    if not rect:
        return None, 0, 0
    img = _grab(rect.width, rect.height, lambda mem, scr: user32.PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT))
    return img, 0, 0


def find_template(hay, tmpl, conf):
    hay = np.ascontiguousarray(hay[:, :, :3])
    th, tw = tmpl.shape[:2]
    if hay.shape[0] < th or hay.shape[1] < tw:
        return None
    res = cv2.matchTemplate(hay, tmpl, cv2.TM_CCOEFF_NORMED)
    _, maxv, _, loc = cv2.minMaxLoc(res)
    if maxv >= conf:
        return loc[0] + tw // 2, loc[1] + th // 2, maxv
    return None


def find_color(hay, rgb, tol):
    target = np.array([rgb[2], rgb[1], rgb[0]], dtype=np.int16)
    diff = np.abs(hay[:, :, :3].astype(np.int16) - target).max(axis=2)
    ys, xs = np.nonzero(diff <= tol)
    if len(xs):
        return int(xs[0]), int(ys[0])
    return None


def _parse_rgb(text):
    rgb = [int(c) for c in str(text).replace(" ", "").split(",")]
    if len(rgb) != 3 or not all(0 <= c <= 255 for c in rgb):
        raise ValueError
    return tuple(rgb)


# ============================================================================
#  AKSİYON TANIMLARI
# ============================================================================
TYPES = [
    ("Click", "🖱  Tıkla"), ("Move", "➜  Fare Taşı"), ("Drag", "✋  Sürükle"),
    ("Press", "⌨  Tuş"), ("Type", "✎  Yazı Yaz"), ("Scroll", "↕  Kaydır"), ("Wait", "⏱  Bekle"),
    ("WaitColor", "🎨  Renk Bekle"), ("IfColor", "❔  Renk Kontrol"),
    ("FindImage", "🔍  Resim Bul"), ("FindColor", "🎯  Renk Ara"),
    ("Label", "🏷  Etiket"), ("Goto", "↩  Git"), ("Notify", "🔔  Bildirim"),
]
TYPE_LABELS = dict(TYPES)
TYPE_FROM_LABEL = {v: k for k, v in TYPES}

BTN = [("left", "Sol"), ("right", "Sağ"), ("middle", "Orta")]
KEYMODE = [("tap", "Bas ve bırak"), ("down", "Basılı tut (bırakma)"), ("up", "Bırak")]
UNTIL = [("appear", "Görünene kadar"), ("vanish", "Kaybolana kadar")]
FOUNDCLICK = [("left", "Sol tıkla"), ("right", "Sağ tıkla"), ("double", "Çift tıkla"),
              ("move", "Sadece imleci götür"), ("none", "Hiçbir şey yapma")]

# (anahtar, etiket, tür, seçenekler/ipucu, varsayılan)
SCHEMA = {
    "Click": [("button", "Fare tuşu", "choice", BTN, "left"),
              ("double", "Çift tıklama", "bool", None, False),
              ("hold", "Basılı tutma süresi (sn) · 0 = normal tık", "float", None, 0.0),
              ("here", "Konum yerine imlecin olduğu yere tıkla", "bool", None, False),
              ("xy", "Konum", "xy", None, None)],
    "Move": [("xy", "Hedef konum (göreli modda: kaydırma miktarı)", "xy", None, None),
             ("relative", "Göreli hareket (FPS oyun kamerası için)", "bool", None, False)],
    "Drag": [("xy", "Başlangıç", "xy", None, None),
             ("xy2", "Bitiş", "xy", None, None),
             ("button", "Fare tuşu", "choice", BTN, "left"),
             ("duration", "Sürükleme süresi (sn)", "float", None, 0.3)],
    "Press": [("key", "Tuş veya kombinasyon", "text", "a, enter, f5, ctrl+c, shift+tab", "enter"),
              ("mode", "Davranış", "choice", KEYMODE, "tap"),
              ("hold", "Basılı tutma süresi (sn) · 'Bas ve bırak' için", "float", None, 0.0)],
    "Type": [("text", "Yazılacak metin (\\n = Enter)", "text", "Merhaba!", ""),
             ("interval", "Harfler arası bekleme (sn)", "float", None, 0.02)],
    "Scroll": [("amount", "Miktar · bir çentik = 120 (yukarı +, aşağı −)", "int", None, -120)],
    "Wait": [],
    "WaitColor": [("color", "Renk (R,G,B)", "color", None, ""),
                  ("xy", "Konum", "xy", None, None),
                  ("tolerance", "Tolerans (0-255)", "int", None, 10),
                  ("until", "Bekleme koşulu", "choice", UNTIL, "appear"),
                  ("timeout", "Zaman aşımı (sn)", "float", None, 5.0),
                  ("on_timeout", "Zaman aşılırsa", "outcome", None, "next")],
    "IfColor": [("color", "Renk (R,G,B)", "color", None, ""),
                ("xy", "Konum", "xy", None, None),
                ("tolerance", "Tolerans (0-255)", "int", None, 10),
                ("on_true", "Renk eşleşirse", "outcome", None, "next"),
                ("on_false", "Eşleşmezse", "outcome", None, "next")],
    "FindImage": [("image", "Aranacak resim", "image", None, ""),
                  ("confidence", "Benzerlik eşiği (0.5 - 1.0)", "float", None, 0.85),
                  ("timeout", "Arama süresi (sn) · 0 = tek bakış", "float", None, 0.0),
                  ("click", "Bulununca", "choice", FOUNDCLICK, "left"),
                  ("on_found", "Bulunursa sonra", "outcome", None, "next"),
                  ("on_missing", "Bulunamazsa", "outcome", None, "next")],
    "FindColor": [("color", "Aranacak renk (R,G,B)", "color", None, ""),
                  ("tolerance", "Tolerans (0-255)", "int", None, 10),
                  ("timeout", "Arama süresi (sn) · 0 = tek bakış", "float", None, 0.0),
                  ("click", "Bulununca", "choice", FOUNDCLICK, "left"),
                  ("on_found", "Bulunursa sonra", "outcome", None, "next"),
                  ("on_missing", "Bulunamazsa", "outcome", None, "next")],
    "Label": [("name", "Etiket adı", "text", "örn. başla", "")],
    "Goto": [("label", "Gidilecek etiket", "labelref", None, ""),
             ("times", "Kaç kez gidilsin (0 = her zaman)", "int", None, 0)],
    "Notify": [("text", "Mesaj", "text", "örn. Envanter doldu", ""),
               ("beep", "Sesli uyarı", "bool", None, True),
               ("stop", "Makroyu durdur", "bool", None, False)],
}
XY_KEYS = {"xy": ("x", "y"), "xy2": ("x2", "y2")}


def _choice_label(choices, value):
    return dict(choices).get(value, choices[0][1])


def _choice_value(choices, label):
    for v, l in choices:
        if l == label:
            return v
    return choices[0][0]


def _outcome_text(v):
    if v == "stop": return "dur"
    if isinstance(v, str) and v.startswith("goto:"): return "→ " + v[5:]
    return "devam"


def _normalize(a):
    """Eski sürüm (V8-V11) dosyalarını da okuyabilmek için eksik alanları tamamlar."""
    a = dict(a)
    t = a.get("type")
    if t not in SCHEMA:
        return None
    a.setdefault("enabled", True)
    a.setdefault("delay", 0)
    if t == "WaitColor" and "timeout" not in a:
        # V8-V11'de WaitColor'ın "delay" alanı zaman aşımıydı
        a["timeout"] = float(a.get("delay") or 5)
        a["delay"] = 0
    for key, _l, kind, _o, default in SCHEMA[t]:
        if kind == "xy":
            for k in XY_KEYS[key]:
                a.setdefault(k, 0)
        else:
            a.setdefault(key, default)
    return a


class _Stop(Exception):
    pass


# ============================================================================
#  TEMA
# ============================================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#0f1115"
SURFACE = "#171a21"
SURFACE2 = "#1f232c"
SURFACE3 = "#282d38"
BORDER = "#2c313c"
TEXT = "#e6e8ee"
MUTED = "#8b93a5"
ACCENT = "#6c8cff"
ACCENT_H = "#5a78e6"
GREEN = "#34c38f"
GREEN_H = "#2aa87a"
RED = "#f46a6a"
RED_H = "#d95757"
AMBER = "#f1b44c"
AMBER_H = "#d99d3a"

FONT = "Segoe UI"


def _cps_to_slider(cps):
    # Logaritmik ölçek: 1-1000 aralığında düşük hızlar da rahat ayarlanır
    return math.log10(max(1.0, min(1000.0, cps))) / 3


def _slider_to_cps(v):
    return max(1, min(1000, round(10 ** (3 * v))))


# ============================================================================
#  UYGULAMA
# ============================================================================
class ShadowMacroV12:
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowMacro V12")
        self.root.geometry("1280x880")
        self.root.minsize(1140, 780)
        self.root.configure(fg_color=BG)

        # --- DURUM ---
        self.is_macro_running = False
        self.is_paused = False
        self.is_f7_running = False
        self.is_recording = False
        self.is_picking = False
        self.editing_index = None

        self.actions = []
        self.mouse_listener = None
        self.rec_kb_listener = None
        self._held = set()
        self._run_info = {}
        self._cur_idx = None
        self._shown_idx = None
        self._log_q = queue.Queue()
        self._tmpl_cache = {}
        self._f7_hwnd = None
        self._f7_pos = (0, 0)
        self._f7_window_mode = False
        self._f7_interval = 0.1
        self._f7_turbo = False
        self._f7_human = True
        self._status_after = None
        self._preview_img = None
        self._pick_target = None

        # --- DEĞİŞKENLER ---
        self.loop_var = tk.StringVar(value="0")
        self.limit_var = tk.StringVar(value="0")
        self.start_delay_var = tk.StringVar(value="0")
        self.human_speed = tk.BooleanVar(value=True)
        self.use_turbo_mode = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)
        self.use_window_mode = tk.BooleanVar(value=False)
        self.target_window_title = tk.StringVar()

        self.f7_cps = 10.0
        self.cps_text = tk.StringVar(value="10")
        self.type_var = tk.StringVar(value=TYPE_LABELS["Click"])
        self.delay_var = tk.StringVar(value="0.1")
        self.fv = {}  # editör alan değişkenleri (tipler arası korunur)

        # Windows zamanlayıcı çözünürlüğünü 1 ms'ye çek (yüksek CPS için şart)
        winmm.timeBeginPeriod(1)

        self.setup_styles()
        self.create_gui()
        self.load_config()
        self.refresh_windows()
        self.refresh_tree()
        self.update_status_pill()

        self.root.update_idletasks()
        self._own_hwnd = user32.GetAncestor(int(self.root.wm_frame(), 16), GA_ROOT)

        self.start_hotkey_listener()
        self.picker_listener = keyboard.Listener(on_release=self.on_picker_key)
        self.picker_listener.daemon = True
        self.picker_listener.start()
        self._track_cursor()
        self._poll()
        if not HAS_CV:
            self.log("Uyarı: opencv-python/numpy kurulu değil — Resim Bul ve Renk Ara çalışmaz.")

    # ================= STİL =================
    def setup_styles(self):
        scale = self.root.winfo_fpixels("1i") / 96
        style = ttk.Style()
        style.theme_use("clam")
        style.layout("Macro.Treeview", [("Macro.Treeview.treearea", {"sticky": "nswe"})])
        style.configure("Macro.Treeview",
                        background=SURFACE2, foreground=TEXT, fieldbackground=SURFACE2,
                        font=(FONT, 10), rowheight=int(32 * scale), borderwidth=0, relief="flat")
        style.map("Macro.Treeview",
                  background=[("selected", ACCENT)], foreground=[("selected", "white")])
        style.configure("Macro.Treeview.Heading",
                        background=SURFACE, foreground=MUTED, font=(FONT, 9, "bold"),
                        relief="flat", borderwidth=0, padding=(8, 6))
        style.map("Macro.Treeview.Heading", background=[("active", SURFACE)])

    # ================= YARDIMCI WIDGET'LAR =================
    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=14, border_width=1, border_color=BORDER)

    def _title(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(FONT, 15, "bold"), text_color=TEXT)

    def _muted(self, parent, text, size=12):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(FONT, size), text_color=MUTED, justify="left")

    def _badge(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(FONT, 11, "bold"), text_color=TEXT,
                            fg_color=SURFACE3, corner_radius=6, width=34, height=22)

    def _entry(self, parent, var, width=None, placeholder=None):
        kw = {"width": width} if width else {}
        return ctk.CTkEntry(parent, textvariable=var, fg_color=SURFACE2, border_color=BORDER,
                            text_color=TEXT, corner_radius=8, height=32,
                            placeholder_text=placeholder, **kw)

    def _ghost_btn(self, parent, text, cmd, width=36):
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=32, corner_radius=8,
                             fg_color=SURFACE2, hover_color=SURFACE3, text_color=TEXT,
                             border_width=1, border_color=BORDER, font=ctk.CTkFont(FONT, 12))

    def _switch(self, parent, text, var, cmd=None, color=ACCENT):
        return ctk.CTkSwitch(parent, text=text, variable=var, command=cmd, onvalue=True, offvalue=False,
                             progress_color=color, button_color="#ffffff", button_hover_color="#dfe3ea",
                             fg_color=SURFACE3, text_color=TEXT, font=ctk.CTkFont(FONT, 12))

    def _option(self, parent, var, values, cmd=None, width=None):
        kw = {"width": width} if width else {}
        return ctk.CTkOptionMenu(parent, variable=var, values=values, command=cmd, height=32, corner_radius=8,
                                 fg_color=SURFACE2, button_color=SURFACE3, button_hover_color=BORDER,
                                 text_color=TEXT, dropdown_fg_color=SURFACE2, dropdown_hover_color=SURFACE3,
                                 dropdown_text_color=TEXT, font=ctk.CTkFont(FONT, 12),
                                 dropdown_font=ctk.CTkFont(FONT, 12), dynamic_resizing=False, **kw)

    # ================= ARAYÜZ =================
    def create_gui(self):
        r = self.root
        r.grid_columnconfigure(0, weight=1)
        r.grid_rowconfigure(2, weight=1)

        # ---------- ÜST BAR ----------
        header = ctk.CTkFrame(r, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 6))
        header.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text="◆", font=ctk.CTkFont(FONT, 24, "bold"), text_color=ACCENT).pack(side="left")
        ctk.CTkLabel(brand, text="ShadowMacro", font=ctk.CTkFont(FONT, 22, "bold"), text_color=TEXT).pack(side="left", padx=(8, 8))
        ctk.CTkLabel(brand, text="V12", font=ctk.CTkFont(FONT, 11, "bold"), text_color=ACCENT,
                     fg_color="#1d2540", corner_radius=6, width=36, height=22).pack(side="left", pady=(4, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e")
        self.status_pill = ctk.CTkLabel(right, text="", font=ctk.CTkFont(FONT, 12, "bold"),
                                        corner_radius=12, height=28, width=160)
        self.status_pill.pack(side="left", padx=(0, 16))
        self._switch(right, "Üstte tut", self.always_on_top, self.toggle_always_on_top).pack(side="left")

        # ---------- HEDEF PENCERE ----------
        target = self._card(r)
        target.grid(row=1, column=0, sticky="ew", padx=20, pady=6)
        target.grid_columnconfigure(1, weight=1)

        tleft = ctk.CTkFrame(target, fg_color="transparent")
        tleft.grid(row=0, column=0, sticky="w", padx=(18, 12), pady=12)
        self._title(tleft, "Hedef Pencere").pack(anchor="w")
        self.lbl_mode_hint = self._muted(tleft, "", 11)
        self.lbl_mode_hint.pack(anchor="w")

        self.cb_window = ctk.CTkComboBox(target, variable=self.target_window_title, values=[], state="readonly",
                                         height=36, corner_radius=8, fg_color=SURFACE2, border_color=BORDER,
                                         button_color=SURFACE3, button_hover_color=BORDER, text_color=TEXT,
                                         dropdown_fg_color=SURFACE2, dropdown_hover_color=SURFACE3,
                                         dropdown_text_color=TEXT, font=ctk.CTkFont(FONT, 12),
                                         command=lambda _: self.update_mode_hint())
        self.cb_window.grid(row=0, column=1, sticky="ew", pady=12)
        self._ghost_btn(target, "↻", self.refresh_windows, width=38).grid(row=0, column=2, padx=8)
        self._switch(target, "Pencere Modu", self.use_window_mode, self.update_mode_hint, GREEN).grid(
            row=0, column=3, padx=(8, 18))

        # ---------- ORTA: LİSTE + EDİTÖR ----------
        mid = ctk.CTkFrame(r, fg_color="transparent")
        mid.grid(row=2, column=0, sticky="nsew", padx=20, pady=6)
        mid.grid_columnconfigure(0, weight=1)
        mid.grid_rowconfigure(0, weight=1)

        self._build_list(mid)
        self._build_editor(mid)

        # ---------- ALT: TIKLAYICI + MAKRO ----------
        bottom = ctk.CTkFrame(r, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=20, pady=6)
        bottom.grid_columnconfigure(0, weight=2)
        bottom.grid_columnconfigure(1, weight=3)
        self._build_clicker(bottom)
        self._build_runner(bottom)

        # ---------- DURUM ÇUBUĞU ----------
        sbar = ctk.CTkFrame(r, fg_color=SURFACE, corner_radius=0, height=30)
        sbar.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        sbar.grid_columnconfigure(0, weight=1)
        self.lbl_status = ctk.CTkLabel(sbar, text="", font=ctk.CTkFont(FONT, 11), text_color=MUTED, anchor="w")
        self.lbl_status.grid(row=0, column=0, sticky="w", padx=16, pady=4)
        self.lbl_cursor = ctk.CTkLabel(sbar, text="", font=ctk.CTkFont("Consolas", 11), text_color=MUTED)
        self.lbl_cursor.grid(row=0, column=1, sticky="e", padx=16)

        # Kısayollar
        r.bind("<Control-s>", lambda e: self.save_project())
        r.bind("<Control-o>", lambda e: self.load_project())

        self.update_mode_hint()
        self.on_type_change()
        self.set_status("Hazır. Aksiyon ekle ya da canlı kayıt başlat.")

    def _build_list(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 0))
        head.grid_columnconfigure(1, weight=1)
        self._title(head, "Makro").grid(row=0, column=0, sticky="w")
        self.lbl_count = ctk.CTkLabel(head, text="0", font=ctk.CTkFont(FONT, 11, "bold"), text_color=MUTED,
                                      fg_color=SURFACE3, corner_radius=10, width=30, height=20)
        self.lbl_count.grid(row=0, column=1, sticky="w", padx=8)
        self.btn_rec = ctk.CTkButton(head, text="🔴  Canlı Kayıt", command=self.toggle_recording, width=130,
                                     height=32, corner_radius=8, fg_color="#3a2328", hover_color="#4a2a30",
                                     text_color=RED, font=ctk.CTkFont(FONT, 12, "bold"))
        self.btn_rec.grid(row=0, column=2, padx=(0, 12))
        self._ghost_btn(head, "📂  Aç", self.load_project, width=72).grid(row=0, column=3, padx=4)
        self._ghost_btn(head, "💾  Kaydet", self.save_project, width=92).grid(row=0, column=4)

        tabs = ctk.CTkTabview(card, fg_color=SURFACE, corner_radius=10, height=200,
                              segmented_button_fg_color=SURFACE2, segmented_button_selected_color=ACCENT,
                              segmented_button_selected_hover_color=ACCENT_H,
                              segmented_button_unselected_color=SURFACE2,
                              segmented_button_unselected_hover_color=SURFACE3, text_color=TEXT, anchor="w")
        tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 4))
        t_list = tabs.add("Aksiyonlar")
        t_log = tabs.add("Günlük")
        self.tabs = tabs

        # --- Aksiyon listesi ---
        t_list.grid_columnconfigure(0, weight=1)
        t_list.grid_rowconfigure(0, weight=1)
        holder = ctk.CTkFrame(t_list, fg_color=SURFACE2, corner_radius=10)
        holder.grid(row=0, column=0, sticky="nsew")
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)

        cols = ("ID", "On", "Type", "Detail", "Delay")
        self.tree = ttk.Treeview(holder, columns=cols, show="headings", selectmode="browse", style="Macro.Treeview")
        self.tree.heading("ID", text="#"); self.tree.column("ID", width=40, anchor="center", stretch=False)
        self.tree.heading("On", text=""); self.tree.column("On", width=26, anchor="center", stretch=False)
        self.tree.heading("Type", text="İşlem", anchor="w"); self.tree.column("Type", width=150, stretch=False)
        self.tree.heading("Detail", text="Detay", anchor="w"); self.tree.column("Detail", width=280)
        self.tree.heading("Delay", text="Bekleme"); self.tree.column("Delay", width=84, anchor="center", stretch=False)
        self.tree.tag_configure("odd", background="#1b1f27")
        self.tree.tag_configure("label", foreground=ACCENT, font=(FONT, 10, "bold"))
        self.tree.tag_configure("flow", foreground="#b9a6ff")
        self.tree.tag_configure("disabled", foreground="#5b6272")
        self.tree.tag_configure("running", background="#4a3b17", foreground="#ffe1a6")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sb = ctk.CTkScrollbar(holder, command=self.tree.yview, fg_color="transparent",
                              button_color=SURFACE3, button_hover_color=BORDER)
        sb.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Delete>", lambda e: self.delete_row())
        self.tree.bind("<space>", lambda e: self.toggle_enabled())
        self.tree.bind("<Escape>", lambda e: self.clear_selection())

        self.lbl_empty = ctk.CTkLabel(holder, text="Henüz aksiyon yok\n\nSağdaki panelden ekle ya da\nCanlı Kayıt ile tıklama ve tuşlarını kaydet",
                                      font=ctk.CTkFont(FONT, 13), text_color=MUTED, fg_color=SURFACE2)

        bar = ctk.CTkFrame(t_list, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(10, 2))
        self._ghost_btn(bar, "▲", lambda: self.move_row(-1)).pack(side="left", padx=(0, 4))
        self._ghost_btn(bar, "▼", lambda: self.move_row(1)).pack(side="left", padx=(0, 4))
        self._ghost_btn(bar, "⧉  Çoğalt", self.duplicate_row, width=86).pack(side="left", padx=(8, 4))
        self._ghost_btn(bar, "⏻  Aç/Kapat", self.toggle_enabled, width=96).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Sil", command=self.delete_row, width=60, height=32, corner_radius=8,
                      fg_color="#3a2328", hover_color="#4a2a30", text_color=RED,
                      font=ctk.CTkFont(FONT, 12, "bold")).pack(side="left", padx=4)
        self._ghost_btn(bar, "Tümünü Temizle", self.clear_all, width=120).pack(side="right")

        # --- Günlük ---
        t_log.grid_columnconfigure(0, weight=1)
        t_log.grid_rowconfigure(0, weight=1)
        self.log_box = ctk.CTkTextbox(t_log, fg_color=SURFACE2, text_color=TEXT, corner_radius=10,
                                      font=ctk.CTkFont("Consolas", 11), wrap="word")
        self.log_box.grid(row=0, column=0, sticky="nsew")
        self.log_box.configure(state="disabled")
        lbar = ctk.CTkFrame(t_log, fg_color="transparent")
        lbar.grid(row=1, column=0, sticky="ew", pady=(10, 2))
        self._ghost_btn(lbar, "Günlüğü Temizle", self.clear_log, width=130).pack(side="right")
        self._muted(lbar, "Koşullar, atlamalar, bildirimler ve hatalar burada görünür.", 11).pack(side="left")

    def _build_editor(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=1, sticky="nsew")
        card.configure(width=390)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 8))
        top.grid_columnconfigure(0, weight=1)
        self.lbl_editor_title = self._title(top, "Yeni Aksiyon")
        self.lbl_editor_title.grid(row=0, column=0, sticky="w")
        self._ghost_btn(top, "＋ Yeni", self.clear_selection, width=70).grid(row=0, column=1)

        self.opt_type = self._option(card, self.type_var, [l for _, l in TYPES], cmd=lambda _: self.on_type_change())
        self.opt_type.configure(height=36, font=ctk.CTkFont(FONT, 13, "bold"))
        self.opt_type.grid(row=1, column=0, sticky="ew", padx=18)

        self.form = ctk.CTkScrollableFrame(card, fg_color="transparent", scrollbar_button_color=SURFACE3,
                                           scrollbar_button_hover_color=BORDER)
        self.form.grid(row=2, column=0, sticky="nsew", padx=(10, 4), pady=(8, 0))
        self.form.grid_columnconfigure(0, weight=1)

        dl = ctk.CTkFrame(card, fg_color="transparent")
        dl.grid(row=3, column=0, sticky="ew", padx=18, pady=(6, 0))
        dl.grid_columnconfigure(0, weight=1)
        self.lbl_delay = self._muted(dl, "")
        self.lbl_delay.grid(row=0, column=0, sticky="w")
        self.ent_delay = self._entry(dl, self.delay_var)
        self.ent_delay.grid(row=1, column=0, sticky="ew")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", padx=18, pady=(12, 0))
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text="＋  Ekle", command=self.add_action, height=40, corner_radius=10,
                      fg_color=GREEN, hover_color=GREEN_H, text_color="#0b1a13",
                      font=ctk.CTkFont(FONT, 13, "bold")).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_update = ctk.CTkButton(btns, text="✓  Güncelle", command=self.update_action, height=40,
                                        corner_radius=10, fg_color=SURFACE2, hover_color=SURFACE3,
                                        text_color=TEXT, border_width=1, border_color=BORDER,
                                        font=ctk.CTkFont(FONT, 13, "bold"), state="disabled")
        self.btn_update.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.lbl_editor_hint = self._muted(card, "", 11)
        self.lbl_editor_hint.configure(wraplength=340)
        self.lbl_editor_hint.grid(row=5, column=0, sticky="w", padx=18, pady=(6, 12))

    def _build_clicker(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 2))
        self._title(head, "Hızlı Tıklayıcı").pack(side="left")
        self._badge(head, "F7").pack(side="left", padx=8)
        self.lbl_f7_status = ctk.CTkLabel(head, text="● Durdu", font=ctk.CTkFont(FONT, 12, "bold"), text_color=MUTED)
        self.lbl_f7_status.pack(side="right")
        self._muted(card, "Pencere modunda editördeki X/Y noktasına sinyal gönderir.", 11).grid(
            row=1, column=0, sticky="w", padx=18)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=18, pady=(10, 14))
        row.grid_columnconfigure(1, weight=1)
        self._muted(row, "CPS").grid(row=0, column=0, padx=(0, 10))
        self.cps_slider = ctk.CTkSlider(row, from_=0, to=1, command=self.on_cps_slide, height=18,
                                        progress_color=AMBER, button_color=AMBER, button_hover_color=AMBER_H,
                                        fg_color=SURFACE3)
        self.cps_slider.grid(row=0, column=1, sticky="ew")
        ent = self._entry(row, self.cps_text, width=60)
        ent.configure(justify="center")
        ent.grid(row=0, column=2, padx=10)
        ent.bind("<Return>", lambda e: self.on_cps_entry())
        ent.bind("<FocusOut>", lambda e: self.on_cps_entry())
        self.btn_f7 = ctk.CTkButton(row, text="▶  Başlat", command=self.toggle_f7_clicker, width=104, height=36,
                                    corner_radius=10, fg_color=AMBER, hover_color=AMBER_H, text_color="#1f1606",
                                    font=ctk.CTkFont(FONT, 13, "bold"))
        self.btn_f7.grid(row=0, column=3)

    def _build_runner(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 2))
        self._title(head, "Makroyu Çalıştır").pack(side="left")
        self._badge(head, "F6").pack(side="left", padx=(8, 4))
        self._muted(head, "başlat/durdur", 11).pack(side="left")
        self._badge(head, "F8").pack(side="left", padx=(10, 4))
        self._muted(head, "duraklat", 11).pack(side="left")

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 0))
        for lbl, var in [("Tekrar · 0 = sonsuz", self.loop_var),
                         ("Süre sınırı (dk) · 0 = yok", self.limit_var),
                         ("Geri sayım (sn)", self.start_delay_var)]:
            box = ctk.CTkFrame(opts, fg_color="transparent")
            box.pack(side="left", padx=(0, 14))
            self._muted(box, lbl, 11).pack(anchor="w")
            self._entry(box, var, width=110).pack(anchor="w")
        sw = ctk.CTkFrame(opts, fg_color="transparent")
        sw.pack(side="left", padx=(4, 0))
        self._switch(sw, "Turbo", self.use_turbo_mode).pack(anchor="w", pady=(0, 4))
        self._switch(sw, "İnsansı", self.human_speed).pack(anchor="w")

        brow = ctk.CTkFrame(card, fg_color="transparent")
        brow.grid(row=2, column=0, sticky="ew", padx=18, pady=(10, 14))
        brow.grid_columnconfigure(0, weight=1)
        self.btn_play = ctk.CTkButton(brow, text="", command=self.toggle_macro, height=44, corner_radius=10,
                                      font=ctk.CTkFont(FONT, 14, "bold"))
        self.btn_play.grid(row=0, column=0, sticky="ew")
        self.btn_pause = ctk.CTkButton(brow, text="❚❚  Duraklat", command=self.toggle_pause, width=130, height=44,
                                       corner_radius=10, fg_color=SURFACE2, hover_color=SURFACE3, text_color=TEXT,
                                       border_width=1, border_color=BORDER, font=ctk.CTkFont(FONT, 13, "bold"),
                                       state="disabled")
        self.btn_pause.grid(row=0, column=1, padx=(8, 0))
        self._set_play_button(False)

    # ================= EDİTÖR FORMU =================
    def _var(self, key, kind="text", default=""):
        if key not in self.fv:
            if kind == "bool":
                self.fv[key] = tk.BooleanVar(value=bool(default))
            else:
                self.fv[key] = tk.StringVar(value="" if default is None else
                                            (f"{default:g}" if isinstance(default, float) else str(default)))
        return self.fv[key]

    @staticmethod
    def _fkey(atype, key, kind):
        """Konum, renk ve resim tipler arasında ortak; diğer alanlar her tipe özel."""
        return key if kind in ("xy", "color", "image") else f"{atype}.{key}"

    def _labels(self):
        return [a.get("name", "") for a in self.actions if a["type"] == "Label" and a.get("name")]

    def _outcome_options(self):
        return ["Devam et", "Makroyu durdur"] + [f"→ {n}" for n in self._labels()]

    @staticmethod
    def _outcome_to_display(v):
        if v == "stop": return "Makroyu durdur"
        if isinstance(v, str) and v.startswith("goto:"): return f"→ {v[5:]}"
        return "Devam et"

    @staticmethod
    def _display_to_outcome(s):
        if s == "Makroyu durdur": return "stop"
        if s.startswith("→ "): return "goto:" + s[2:]
        return "next"

    def current_type(self):
        return TYPE_FROM_LABEL.get(self.type_var.get(), "Click")

    def on_type_change(self):
        atype = self.current_type()
        for w in self.form.winfo_children():
            w.destroy()
        self._pick_buttons = {}
        self._img_preview_lbl = None
        self.is_picking = False
        row = 0

        def label(text):
            nonlocal row
            lbl = self._muted(self.form, text)
            lbl.configure(wraplength=330)
            lbl.grid(row=row, column=0, sticky="w", padx=8, pady=(8, 0))
            row += 1

        for key, text, kind, opt, default in SCHEMA[atype]:
            if kind == "xy":
                kx, ky = XY_KEYS[key]
                label(text)
                f = ctk.CTkFrame(self.form, fg_color="transparent")
                f.grid(row=row, column=0, sticky="ew", padx=8); row += 1
                f.grid_columnconfigure((1, 3), weight=1)
                self._muted(f, "X").grid(row=0, column=0, padx=(0, 6))
                self._entry(f, self._var(kx, "int", 0)).grid(row=0, column=1, sticky="ew")
                self._muted(f, "Y").grid(row=0, column=2, padx=(10, 6))
                self._entry(f, self._var(ky, "int", 0)).grid(row=0, column=3, sticky="ew")
                b = self._ghost_btn(self.form, "", None)
                b.grid(row=row, column=0, sticky="ew", padx=8, pady=(6, 0)); row += 1
                self._pick_buttons[key] = b
                self._reset_pick_button(key)
            elif kind == "color":
                label(text)
                f = ctk.CTkFrame(self.form, fg_color="transparent")
                f.grid(row=row, column=0, sticky="ew", padx=8); row += 1
                f.grid_columnconfigure(0, weight=1)
                var = self._var("color", "text", "")
                self._entry(f, var).grid(row=0, column=0, sticky="ew")
                sw = ctk.CTkFrame(f, width=32, height=32, corner_radius=8, fg_color=SURFACE2,
                                  border_width=1, border_color=BORDER)
                sw.grid(row=0, column=1, padx=(8, 0))
                self._swatch = sw
                if not getattr(self, "_color_traced", False):
                    var.trace_add("write", lambda *_: self._update_swatch())
                    self._color_traced = True
                self._update_swatch()
                b = self._ghost_btn(self.form, "", None)
                b.grid(row=row, column=0, sticky="ew", padx=8, pady=(6, 0)); row += 1
                self._pick_buttons["color"] = b
                self._reset_pick_button("color")
            elif kind == "choice":
                label(text)
                var = self._var(self._fkey(atype, key, kind), "text", _choice_label(opt, default))
                if var.get() not in [l for _, l in opt]:
                    var.set(_choice_label(opt, default))
                self._option(self.form, var, [l for _, l in opt]).grid(row=row, column=0, sticky="ew", padx=8); row += 1
            elif kind == "bool":
                var = self._var(self._fkey(atype, key, kind), "bool", default)
                ctk.CTkCheckBox(self.form, text=text, variable=var, onvalue=True, offvalue=False,
                                fg_color=ACCENT, hover_color=ACCENT_H, border_color=BORDER, text_color=TEXT,
                                font=ctk.CTkFont(FONT, 12), corner_radius=6).grid(
                    row=row, column=0, sticky="w", padx=8, pady=(10, 0)); row += 1
            elif kind in ("text", "int", "float"):
                label(f"{text}  ·  {opt}" if kind == "text" and opt else text)
                self._entry(self.form, self._var(self._fkey(atype, key, kind), kind, default)).grid(
                    row=row, column=0, sticky="ew", padx=8); row += 1
            elif kind == "outcome":
                label(text)
                var = self._var(self._fkey(atype, key, kind), "text", "Devam et")
                opts = self._outcome_options()
                if var.get() not in opts:
                    var.set("Devam et")
                self._option(self.form, var, opts).grid(row=row, column=0, sticky="ew", padx=8); row += 1
            elif kind == "labelref":
                label(text)
                var = self._var(self._fkey(atype, key, kind), "text", "")
                labels = self._labels()
                if labels and var.get() not in labels:
                    var.set(labels[0])
                if labels:
                    self._option(self.form, var, labels).grid(row=row, column=0, sticky="ew", padx=8)
                else:
                    var.set("")
                    ctk.CTkLabel(self.form, text="Önce listeye bir 🏷 Etiket ekle.", text_color=AMBER,
                                 font=ctk.CTkFont(FONT, 12)).grid(row=row, column=0, sticky="w", padx=8)
                row += 1
            elif kind == "image":
                label(text)
                self._var("image", "text", "")
                self._var("img_w", "text", "0"); self._var("img_h", "text", "0")
                prev = tk.Label(self.form, text="Resim seçilmedi", bg=SURFACE2, fg=MUTED, font=(FONT, 10),
                                height=4, bd=0)
                prev.grid(row=row, column=0, sticky="ew", padx=8, ipady=6); row += 1
                self._img_preview_lbl = prev
                self._update_image_preview()
                ctk.CTkButton(self.form, text="📷  Ekrandan Seç", command=self.capture_template, height=32,
                              corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_H,
                              font=ctk.CTkFont(FONT, 12, "bold")).grid(row=row, column=0, sticky="ew", padx=8, pady=(6, 0))
                row += 1

        if atype == "Wait":
            ctk.CTkLabel(self.form, text="Sadece aşağıdaki süre kadar bekler.\nRastgele bekleme için '1-3' gibi aralık yaz.",
                         text_color=MUTED, justify="left", font=ctk.CTkFont(FONT, 12)).grid(
                row=row, column=0, sticky="w", padx=8, pady=8)

        if atype == "Label":
            self.lbl_delay.configure(text="Etiketler beklemez, Git aksiyonları için işarettir.")
            self.ent_delay.grid_remove()
        else:
            self.ent_delay.grid()
            self.lbl_delay.configure(text="Bekleme süresi (sn) · '1-3' = rastgele aralık" if atype == "Wait"
                                     else "Öncesinde bekle (sn) · '1-3' = rastgele aralık")
        self._update_editor_hint()

    def _update_editor_hint(self):
        if self.editing_index is None:
            self.lbl_editor_hint.configure(text="Listeden bir satır seçersen burada düzenleyebilirsin. "
                                                "Satır seçiliyken Ekle, yeni aksiyonu onun altına koyar.")
        else:
            self.lbl_editor_hint.configure(text="Değiştirip Güncelle'ye bas. Ekle, kopyasını altına ekler.")

    def _reset_pick_button(self, key):
        b = self._pick_buttons.get(key)
        if not b:
            return
        text = "🎨  Renk ve Konum Seç   (X)" if key == "color" else "🎯  Konum Seç   (X)"
        if key == "xy2":
            text = "🎯  Bitiş Konumunu Seç   (X)"
        b.configure(text=text, command=lambda k=key: self.start_picker(k), fg_color=SURFACE2,
                    hover_color=SURFACE3, text_color=TEXT, border_width=1)

    def _update_swatch(self):
        sw = getattr(self, "_swatch", None)
        if not sw or not sw.winfo_exists():
            return
        try:
            r, g, b = _parse_rgb(self.fv["color"].get())
            sw.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")
        except Exception:
            sw.configure(fg_color=SURFACE2)

    def _update_image_preview(self):
        lbl = self._img_preview_lbl
        if not lbl or not lbl.winfo_exists():
            return
        data = self.fv["image"].get()
        if not data:
            lbl.configure(text="Resim seçilmedi", image="", height=4)
            return
        try:
            img = tk.PhotoImage(data=data)
            factor = max(1, math.ceil(img.width() / 320), math.ceil(img.height() / 140))
            if factor > 1:
                img = img.subsample(factor)
            self._preview_img = img
            lbl.configure(text="", image=img, height=img.height())
        except Exception:
            lbl.configure(text=f"Resim {self.fv['img_w'].get()}×{self.fv['img_h'].get()} px")

    def _editor_action(self):
        """Editördeki değerlerden aksiyon üretir; hatalıysa ValueError(mesaj)."""
        atype = self.current_type()
        act = {"type": atype}
        if atype != "Label":
            try:
                act["delay"] = _parse_delay(self.delay_var.get())
            except ValueError:
                raise ValueError("Bekleme süresi sayı (0.5) ya da aralık (1-3) olmalı.")
        else:
            act["delay"] = 0
        for key, text, kind, opt, default in SCHEMA[atype]:
            fk = self._fkey(atype, key, kind)
            if kind == "xy":
                for k in XY_KEYS[key]:
                    try:
                        act[k] = int(self.fv[k].get())
                    except ValueError:
                        raise ValueError("Koordinatlar tam sayı olmalı.")
            elif kind == "color":
                try:
                    act["color"] = ",".join(map(str, _parse_rgb(self.fv["color"].get())))
                except ValueError:
                    raise ValueError("Renk “R,G,B” biçiminde olmalı (0-255).")
            elif kind == "choice":
                act[key] = _choice_value(opt, self.fv[fk].get())
            elif kind == "bool":
                act[key] = bool(self.fv[fk].get())
            elif kind == "int":
                try:
                    act[key] = int(self.fv[fk].get())
                except ValueError:
                    raise ValueError(f"“{text}” tam sayı olmalı.")
            elif kind == "float":
                try:
                    act[key] = float(self.fv[fk].get().replace(",", "."))
                except ValueError:
                    raise ValueError(f"“{text}” sayı olmalı.")
            elif kind == "text":
                act[key] = self.fv[fk].get()
            elif kind == "outcome":
                act[key] = self._display_to_outcome(self.fv[fk].get())
            elif kind == "labelref":
                act[key] = self.fv[fk].get()
            elif kind == "image":
                act["image"] = self.fv["image"].get()
                act["img_w"] = int(self.fv["img_w"].get() or 0)
                act["img_h"] = int(self.fv["img_h"].get() or 0)

        # tipe özel kontroller
        if atype == "Press":
            try:
                _parse_keys(act["key"])
            except ValueError as e:
                raise ValueError(f"{e}. Örnek: a, enter, f5, ctrl+c")
        if atype == "Type" and not act["text"]:
            raise ValueError("Yazılacak metni gir.")
        if atype == "Label":
            name = act["name"].strip()
            if not name:
                raise ValueError("Etikete bir ad ver.")
            others = [a.get("name") for i, a in enumerate(self.actions)
                      if a["type"] == "Label" and i != self.editing_index]
            if name in others:
                raise ValueError(f"“{name}” adlı bir etiket zaten var.")
            act["name"] = name
        if atype == "Goto" and not act["label"]:
            raise ValueError("Önce listeye bir Etiket ekle.")
        if atype == "FindImage":
            if not act["image"]:
                raise ValueError("📷 Ekrandan Seç ile aranacak resmi seç.")
            if not HAS_CV:
                raise ValueError("Resim Bul için: pip install opencv-python numpy")
            if not 0.3 <= act["confidence"] <= 1.0:
                raise ValueError("Benzerlik eşiği 0.3 ile 1.0 arasında olmalı.")
        if atype == "FindColor" and not HAS_CV:
            raise ValueError("Renk Ara için: pip install opencv-python numpy")
        if atype in ("WaitColor", "IfColor", "FindColor") and not 0 <= act["tolerance"] <= 255:
            raise ValueError("Tolerans 0-255 arasında olmalı.")
        return act

    def _load_into_editor(self, a):
        atype = a["type"]
        self.type_var.set(TYPE_LABELS[atype])
        d = a.get("delay", 0)
        self.delay_var.set(d if isinstance(d, str) else f"{float(d):g}")
        for key, text, kind, opt, default in SCHEMA[atype]:
            fk = self._fkey(atype, key, kind)
            if kind == "xy":
                for k in XY_KEYS[key]:
                    self._var(k, "int", 0).set(str(a.get(k, 0)))
            elif kind == "color":
                self._var("color").set(a.get("color", ""))
            elif kind == "choice":
                self._var(fk).set(_choice_label(opt, a.get(key, default)))
            elif kind == "bool":
                self._var(fk, "bool", default).set(bool(a.get(key, default)))
            elif kind in ("int", "float"):
                v = a.get(key, default)
                self._var(fk, kind, default).set(f"{v:g}" if isinstance(v, float) else str(v))
            elif kind in ("text", "labelref"):
                self._var(fk).set(a.get(key, default) or "")
            elif kind == "outcome":
                self._var(fk).set(self._outcome_to_display(a.get(key, "next")))
            elif kind == "image":
                self._var("image").set(a.get("image", ""))
                self._var("img_w").set(str(a.get("img_w", 0)))
                self._var("img_h").set(str(a.get("img_h", 0)))
        self.on_type_change()

    # ================= UI DURUMU =================
    def set_status(self, text, kind="info", timeout=None):
        color = {"info": MUTED, "ok": GREEN, "error": RED, "warn": AMBER}[kind]
        self.lbl_status.configure(text=text, text_color=color)
        if self._status_after:
            self.root.after_cancel(self._status_after)
            self._status_after = None
        if timeout:
            def expire():
                self._status_after = None
                self.lbl_status.configure(text="", text_color=MUTED)
            self._status_after = self.root.after(timeout, expire)

    def log(self, msg):
        """Thread-safe: herhangi bir thread'den çağrılabilir."""
        self._log_q.put(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def update_status_pill(self):
        if self.is_recording:
            text, fg, bg = "● Kayıt yapılıyor", RED, "#3a2328"
        elif self.is_macro_running and self.is_paused:
            text, fg, bg = "❚❚ Duraklatıldı", AMBER, "#3a2f1a"
        elif self.is_macro_running:
            text, fg, bg = "● Makro çalışıyor", ACCENT, "#1d2540"
        elif self.is_f7_running:
            text, fg, bg = "● Tıklayıcı aktif", AMBER, "#3a2f1a"
        else:
            text, fg, bg = "● Hazır", GREEN, "#163328"
        self.status_pill.configure(text=text, text_color=fg, fg_color=bg)

    def update_mode_hint(self):
        if self.use_window_mode.get():
            if self.target_window_title.get():
                self.lbl_mode_hint.configure(text="Açık · Fare ve klavye kullanılmaz, komutlar seçili pencereye sinyal olarak gider.", text_color=GREEN)
            else:
                self.lbl_mode_hint.configure(text="Açık · Önce bir hedef pencere seç.", text_color=AMBER)
        else:
            self.lbl_mode_hint.configure(text="Kapalı · Gerçek fare ve klavye kullanılır (oyunlarla en uyumlu mod).", text_color=MUTED)

    def _set_play_button(self, running):
        if running:
            self.btn_play.configure(text="⏹  Durdur   (F6)", fg_color=RED, hover_color=RED_H, text_color="white")
            self.btn_pause.configure(state="normal")
        else:
            self.btn_play.configure(text="▶  Makroyu Başlat   (F6)", fg_color=ACCENT, hover_color=ACCENT_H, text_color="white")
            self.btn_pause.configure(state="disabled", text="❚❚  Duraklat", fg_color=SURFACE2, text_color=TEXT)

    def _set_f7_ui(self, running):
        if running:
            self.btn_f7.configure(text="⏹  Durdur", fg_color=RED, hover_color=RED_H, text_color="white")
            self.lbl_f7_status.configure(text="● Aktif", text_color=AMBER)
        else:
            self.btn_f7.configure(text="▶  Başlat", fg_color=AMBER, hover_color=AMBER_H, text_color="#1f1606")
            self.lbl_f7_status.configure(text="● Durdu", text_color=MUTED)
        self.update_status_pill()

    def _track_cursor(self):
        try:
            x, y = _cursor_pos()
            suffix = ""
            if self.use_window_mode.get():
                win = self.get_window_rect()
                if win:
                    x -= win.left; y -= win.top
                    suffix = "  (pencereye göre)"
            self.lbl_cursor.configure(text=f"İmleç  X {x:>5}  Y {y:>5}{suffix}")
        except Exception:
            pass
        self.root.after(100, self._track_cursor)

    def _poll(self):
        # günlük
        lines = []
        try:
            while len(lines) < 300:
                lines.append(self._log_q.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", "".join(lines))
            count = int(self.log_box.index("end-1c").split(".")[0])
            if count > 1000:
                self.log_box.delete("1.0", f"{count - 1000}.0")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        # çalışan satır vurgusu + durum metni
        idx = self._cur_idx if self.is_macro_running else None
        if idx != self._shown_idx:
            children = self.tree.get_children()
            if self._shown_idx is not None and self._shown_idx < len(children):
                self.tree.item(children[self._shown_idx], tags=self._row_tags(self._shown_idx))
            if idx is not None and idx < len(children):
                self.tree.item(children[idx], tags=self._row_tags(idx) + ("running",))
                self.tree.see(children[idx])
            self._shown_idx = idx
        if self.is_macro_running and self._status_after is None:
            info = self._run_info
            if info.get("countdown"):
                self.lbl_status.configure(text=f"Başlıyor: {info['countdown']} …", text_color=AMBER)
            elif info.get("start"):
                el = int(time.time() - info["start"])
                total = f"/{info['loops']}" if info.get("loops") else ""
                pause = "  ·  DURAKLATILDI (F8 ile devam)" if self.is_paused else ""
                self.lbl_status.configure(
                    text=f"Makro çalışıyor · tur {info.get('loop', 1)}{total} · adım #{(info.get('pc') or 0) + 1}"
                         f" · {el // 60:02d}:{el % 60:02d}{pause}",
                    text_color=AMBER if self.is_paused else MUTED)
        self.root.after(100, self._poll)

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

    # ================= PENCERE YÖNETİMİ =================
    def refresh_windows(self):
        try:
            own = self.root.title()
            wins = sorted(w for w in _get_all_windows() if w != own)
            self.cb_window.configure(values=wins)
            cur = self.target_window_title.get()
            if cur and cur not in wins:
                self.set_status(f"“{cur}” penceresi şu an açık değil.", "warn", 4000)
            else:
                self.set_status(f"{len(wins)} pencere bulundu.", "info", 2500)
        except Exception:
            pass
        self.update_mode_hint()

    def get_window_rect(self):
        title = self.target_window_title.get()
        if not title:
            return None
        return _get_window_rect(title)

    # ================= LİSTE İŞLEMLERİ =================
    def add_action(self):
        try:
            act = self._editor_action()
        except ValueError as e:
            self.set_status(str(e), "error", 5000)
            return
        act["enabled"] = True
        sel = self._selected_index()
        idx = len(self.actions) if sel is None else sel + 1
        self.actions.insert(idx, act)
        self.refresh_tree()
        self._select(idx)
        self.set_status(f"{TYPE_LABELS[act['type']].split()[-1]} aksiyonu #{idx + 1} olarak eklendi.", "ok", 2500)

    def update_action(self):
        idx = self.editing_index
        if idx is None or idx >= len(self.actions):
            return
        try:
            act = self._editor_action()
        except ValueError as e:
            self.set_status(str(e), "error", 5000)
            return
        old = self.actions[idx]
        act["enabled"] = old.get("enabled", True)
        # etiket adı değiştiyse ona giden Git/sonuçları da güncelle
        if old["type"] == "Label" and act["type"] == "Label" and old.get("name") != act["name"]:
            self._rename_label(old.get("name"), act["name"])
        self.actions[idx] = act
        self.refresh_tree()
        self._select(idx)
        self.set_status(f"#{idx + 1} güncellendi.", "ok", 2500)

    def _rename_label(self, old, new):
        for a in self.actions:
            if a["type"] == "Goto" and a.get("label") == old:
                a["label"] = new
            for k in ("on_timeout", "on_true", "on_false", "on_found", "on_missing"):
                if a.get(k) == f"goto:{old}":
                    a[k] = f"goto:{new}"

    def on_tree_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            self.editing_index = None
            self.lbl_editor_title.configure(text="Yeni Aksiyon")
            self.btn_update.configure(state="disabled", fg_color=SURFACE2, text_color=TEXT)
            self._update_editor_hint()
            return
        idx = self.tree.index(sel[0])
        if idx >= len(self.actions):
            return
        self.editing_index = idx
        self._load_into_editor(self.actions[idx])
        self.lbl_editor_title.configure(text=f"Aksiyon #{idx + 1}")
        self.btn_update.configure(state="normal", fg_color=ACCENT, hover_color=ACCENT_H, text_color="white")
        self._update_editor_hint()

    def clear_selection(self):
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self.on_tree_select()

    def _select(self, idx):
        children = self.tree.get_children()
        if 0 <= idx < len(children):
            self.tree.selection_set(children[idx])
            self.tree.see(children[idx])

    def _selected_index(self):
        sel = self.tree.selection()
        return self.tree.index(sel[0]) if sel else None

    def _detail(self, a):
        t = a["type"]
        xy = f"{a.get('x')}, {a.get('y')}"
        if t == "Click":
            s = f"{_choice_label(BTN, a['button'])}{' çift' if a.get('double') else ''} tık"
            s += "  ·  imleç konumunda" if a.get("here") else f"  @  {xy}"
            if a.get("hold"): s += f"  ·  {a['hold']:g} sn basılı"
            return s
        if t == "Move":
            return f"göreli  {a['x']:+d}, {a['y']:+d}" if a.get("relative") else f"→  {xy}"
        if t == "Drag":
            return f"{xy}  →  {a['x2']}, {a['y2']}  ·  {_choice_label(BTN, a['button'])}"
        if t == "Press":
            s = a.get("key", "")
            if a.get("mode") != "tap": s += f"  ·  {_choice_label(KEYMODE, a['mode']).lower()}"
            elif a.get("hold"): s += f"  ·  {a['hold']:g} sn basılı"
            return s
        if t == "Type":
            txt = a.get("text", "")
            return f"“{txt[:40]}{'…' if len(txt) > 40 else ''}”"
        if t == "Scroll":
            return f"{a['amount']:+d}"
        if t == "Wait":
            return "bekle"
        if t == "WaitColor":
            s = f"RGB({a['color']}) @ {xy}  ·  {_choice_label(UNTIL, a['until']).lower()}  ·  ≤ {a['timeout']:g} sn"
            if a.get("on_timeout", "next") != "next": s += f"  ·  aşılırsa {_outcome_text(a['on_timeout'])}"
            return s
        if t == "IfColor":
            return f"RGB({a['color']}) @ {xy}  ?  {_outcome_text(a['on_true'])}  :  {_outcome_text(a['on_false'])}"
        if t in ("FindImage", "FindColor"):
            what = f"resim {a.get('img_w', 0)}×{a.get('img_h', 0)}" if t == "FindImage" else f"RGB({a['color']})"
            s = f"{what}  ·  {_choice_label(FOUNDCLICK, a['click']).lower()}"
            if a.get("timeout"): s += f"  ·  ≤ {a['timeout']:g} sn"
            if a.get("on_found", "next") != "next": s += f"  ·  varsa {_outcome_text(a['on_found'])}"
            if a.get("on_missing", "next") != "next": s += f"  ·  yoksa {_outcome_text(a['on_missing'])}"
            return s
        if t == "Label":
            return a.get("name", "")
        if t == "Goto":
            return f"→  {a.get('label', '')}" + (f"  ·  {a['times']} kez" if a.get("times") else "  ·  her zaman")
        if t == "Notify":
            s = a.get("text", "") or "(mesajsız)"
            if a.get("beep"): s += "  ·  🔊"
            if a.get("stop"): s += "  ·  durdurur"
            return s
        return ""

    def _row_tags(self, i):
        a = self.actions[i]
        tags = ["odd"] if i % 2 else []
        if a["type"] == "Label": tags.append("label")
        elif a["type"] in ("Goto", "IfColor"): tags.append("flow")
        if not a.get("enabled", True): tags.append("disabled")
        return tuple(tags)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self._shown_idx = None
        for i, a in enumerate(self.actions):
            t = a["type"]
            if t == "Label":
                delay = ""
            elif t in ("WaitColor",):
                delay = _fmt_delay(a.get("delay", 0)) if a.get("delay") else "—"
            else:
                delay = _fmt_delay(a.get("delay", 0))
            on = "●" if a.get("enabled", True) else "○"
            self.tree.insert("", "end", values=(i + 1, on, TYPE_LABELS.get(t, t), self._detail(a), delay),
                             tags=self._row_tags(i))
        self.lbl_count.configure(text=str(len(self.actions)))
        if self.actions:
            self.lbl_empty.place_forget()
        else:
            self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")

    def delete_row(self):
        idx = self._selected_index()
        if idx is None:
            self.set_status("Silmek için listeden bir satır seç.", "warn", 2500)
            return
        del self.actions[idx]
        self.refresh_tree()
        if self.actions:
            self._select(min(idx, len(self.actions) - 1))
        else:
            self.clear_selection()

    def duplicate_row(self):
        idx = self._selected_index()
        if idx is None:
            self.set_status("Çoğaltmak için listeden bir satır seç.", "warn", 2500)
            return
        copy = dict(self.actions[idx])
        if copy["type"] == "Label":
            base, n = copy["name"], 2
            while f"{base} {n}" in self._labels():
                n += 1
            copy["name"] = f"{base} {n}"
        self.actions.insert(idx + 1, copy)
        self.refresh_tree()
        self._select(idx + 1)

    def toggle_enabled(self):
        idx = self._selected_index()
        if idx is None:
            self.set_status("Açıp kapatmak için listeden bir satır seç.", "warn", 2500)
            return
        a = self.actions[idx]
        a["enabled"] = not a.get("enabled", True)
        self.refresh_tree()
        self._select(idx)
        self.set_status(f"#{idx + 1} {'açıldı' if a['enabled'] else 'devre dışı bırakıldı (atlanır)'}.", "info", 2500)

    def move_row(self, d):
        idx = self._selected_index()
        if idx is None: return
        n = idx + d
        if 0 <= n < len(self.actions):
            self.actions[idx], self.actions[n] = self.actions[n], self.actions[idx]
            self.refresh_tree()
            self._select(n)

    def clear_all(self):
        if not self.actions: return
        if messagebox.askyesno("Temizle", f"{len(self.actions)} aksiyonun tamamı silinsin mi?"):
            self.actions.clear()
            self.refresh_tree()
            self.clear_selection()

    def save_project(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Makro", "*.json")])
        if f:
            with open(f, 'w', encoding="utf-8") as file: json.dump(self.actions, file, indent=2, ensure_ascii=False)
            self.set_status(f"Kaydedildi: {os.path.basename(f)}", "ok", 3000)

    def load_project(self):
        f = filedialog.askopenfilename(filetypes=[("Makro", "*.json"), ("Tümü", "*.*")])
        if not f:
            return
        try:
            with open(f, 'r', encoding="utf-8") as file:
                raw = json.load(file)
            acts = [n for n in (_normalize(a) for a in raw) if n]
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya açılamadı:\n{e}")
            return
        self.actions = acts
        self.refresh_tree()
        self.clear_selection()
        skipped = len(raw) - len(acts)
        msg = f"Açıldı: {os.path.basename(f)} · {len(acts)} aksiyon"
        if skipped:
            msg += f" ({skipped} tanınmayan satır atlandı)"
        self.set_status(msg, "ok", 4000)

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

    # ================= KISAYOLLAR =================
    def start_hotkey_listener(self):
        def on_press(key):
            if key == Key.f6: self.root.after(0, self.toggle_macro)
            elif key == Key.f7: self.root.after(0, self.toggle_f7_clicker)
            elif key == Key.f8: self.root.after(0, self.toggle_pause)
        self.hotkey_listener = keyboard.Listener(on_press=on_press)
        self.hotkey_listener.daemon = True
        self.hotkey_listener.start()

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

    # --- çalışma zamanı yardımcıları (worker thread) ---
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

    # ================= AYARLAR =================
    def load_config(self):
        d = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as f: d = json.load(f)
            except Exception:
                d = {}
        self.set_cps(d.get("f7", 10))
        self.use_turbo_mode.set(d.get("turbo", False))
        self.human_speed.set(d.get("human", True))
        self.loop_var.set(str(d.get("loops", 0)))
        self.limit_var.set(f"{d.get('limit', 0):g}")
        self.start_delay_var.set(f"{d.get('start_delay', 0):g}")
        self.use_window_mode.set(d.get("window_mode", False))
        self.target_window_title.set(d.get("target", ""))
        self.always_on_top.set(d.get("top", False))
        self.toggle_always_on_top()
        self.update_mode_hint()

    def save_config(self):
        def num(var, cast):
            try:
                return max(0, cast(str(var.get()).replace(",", ".") or 0))
            except ValueError:
                return 0
        d = {"f7": self.f7_cps, "turbo": self.use_turbo_mode.get(), "human": self.human_speed.get(),
             "loops": num(self.loop_var, int), "limit": num(self.limit_var, float),
             "start_delay": num(self.start_delay_var, float), "top": self.always_on_top.get(),
             "window_mode": self.use_window_mode.get(), "target": self.target_window_title.get()}
        try:
            with open(CONFIG_PATH, "w") as f: json.dump(d, f)
        except Exception:
            pass

    def toggle_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    def on_close(self):
        self.is_macro_running = False
        self.is_f7_running = False
        self._release_all()
        self.save_config()
        winmm.timeEndPeriod(1)
        self.root.destroy()
        os._exit(0)


if __name__ == "__main__":
    root = ctk.CTk()
    app = ShadowMacroV12(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

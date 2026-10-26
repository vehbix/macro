"""PENCERE SİNYALLERİ (gerçek fare/klavye kullanılmaz).

Koordinatlar pencerenin sol-üst köşesine (GetWindowRect) göredir.
"""
from .winapi import user32, WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_MOUSEMOVE, WM_MOUSEWHEEL, VK_RETURN, _EXTENDED
from .windows import _hwnd_rect, _make_lparam, _target_at, _focus_target

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

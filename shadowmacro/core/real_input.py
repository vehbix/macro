"""GERÇEK GİRİŞ (SendInput, scancode — DirectInput oyunları da algılar)."""
import ctypes

from .winapi import (user32, INPUT, MOUSEINPUT, KEYBDINPUT, INPUT_MOUSE, INPUT_KEYBOARD,
                     KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE, KEYEVENTF_SCANCODE,
                     MOUSEEVENTF_MOVE, MOUSEEVENTF_WHEEL, VK_RETURN, _EXTENDED)

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

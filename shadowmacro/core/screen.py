"""EKRAN OKUMA: piksel, ekran/pencere görüntüsü, şablon ve renk arama."""
import ctypes

from .cv import np, cv2
from .winapi import user32, gdi32, BITMAPINFO, BITMAPINFOHEADER, PW_RENDERFULLCONTENT, SRCCOPY, CAPTUREBLT
from .windows import _hwnd_rect


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

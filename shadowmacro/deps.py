"""Eksik bağımlılıkları açılışta pip ile otomatik kurar.

Bu modül yalnızca standart kütüphaneyi kullanır; böylece paketler eksikken de
içe aktarılabilir. Listeyi değiştirirsen requirements.txt'yi de güncelle.
"""
import importlib
import importlib.util
import subprocess
import sys

# (içe aktarma adı, pip paketi)
REQUIRED = [
    ("customtkinter", "customtkinter>=5.2"),
    ("pynput", "pynput>=1.7"),
    ("pyautogui", "pyautogui>=0.9.54"),
]
# Kurulamazsa uygulama yine açılır; Resim Bul ve Renk Ara devre dışı kalır.
OPTIONAL = [
    ("numpy", "numpy>=1.24"),
    ("cv2", "opencv-python>=4.8"),
]


def _missing(deps):
    return [pkg for mod, pkg in deps if importlib.util.find_spec(mod) is None]


def _pip(args):
    """pip'i bu yorumlayıcıyla çalıştırır; başarılıysa True."""
    # pythonw ile (konsolsuz) açıldıysa her pip çağrısı için siyah pencere açılmasın
    flags = subprocess.CREATE_NO_WINDOW if sys.stdout is None else 0
    cmd = [sys.executable, "-m", "pip", *args, "--disable-pip-version-check"]
    try:
        return subprocess.call(cmd, creationflags=flags) == 0
    except OSError:
        return False


def _ensure_pip():
    if importlib.util.find_spec("pip") is not None:
        return True
    flags = subprocess.CREATE_NO_WINDOW if sys.stdout is None else 0
    try:
        return subprocess.call([sys.executable, "-m", "ensurepip", "--upgrade"], creationflags=flags) == 0
    except OSError:
        return False


def _fatal(msg):
    print(msg, file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("ShadowMacro", msg)
        root.destroy()
    except Exception:
        pass
    raise SystemExit(1)


def ensure_requirements(optional=True):
    """Eksik paketleri kurar. Zorunlu paket kurulamazsa hata gösterip çıkar."""
    required = _missing(REQUIRED)
    extra = _missing(OPTIONAL) if optional else []
    if not required and not extra:
        return

    print(f"Eksik paketler kuruluyor: {', '.join(required + extra)}")
    if not _ensure_pip():
        if required:
            _fatal("pip bulunamadı, paketler kurulamıyor.\n"
                   f"Elle kur: python -m pip install {' '.join(required)}")
        return

    if required and not _pip(["install", *required]):
        _fatal("Zorunlu paketler kurulamadı:\n" + "\n".join(required) +
               "\n\nElle kur: python -m pip install -r requirements.txt")
    if extra and not _pip(["install", *extra]):
        print("Uyarı: isteğe bağlı paketler kurulamadı; Resim Bul ve Renk Ara çalışmayacak.", file=sys.stderr)

    importlib.invalidate_caches()
    still = _missing(REQUIRED)
    if still:
        _fatal("Kurulumdan sonra hâlâ eksik: " + ", ".join(still) +
               "\nProgramı yeniden başlatmayı dene.")

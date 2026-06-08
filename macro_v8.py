import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import time
import threading
import random
import json
import os
import platform
import subprocess
from pynput import mouse, keyboard
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button, Controller as MouseController

# --- GÜVENLİK ---
pyautogui.FAILSAFE = True

# --- PLATFORM TESPİTİ ---
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import ctypes
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004

_mouse_ctrl = MouseController()

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = IS_WINDOWS
except (ImportError, NotImplementedError):
    HAS_PYGETWINDOW = False


# --- PLATFORM YARDIMCILARI ---

def _turbo_click(tx=None, ty=None):
    if IS_WINDOWS:
        if tx is not None and ty is not None:
            ctypes.windll.user32.SetCursorPos(int(tx), int(ty))
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    else:
        if tx is not None and ty is not None:
            _mouse_ctrl.position = (int(tx), int(ty))
        _mouse_ctrl.press(Button.left)
        _mouse_ctrl.release(Button.left)


class _WinRect:
    def __init__(self, left, top):
        self.left = left
        self.top = top


def _get_pixel(x, y):
    # Method 1: pyautogui (X11 veya gnome-screenshot kuruluysa Wayland'da çalışır)
    try:
        return pyautogui.pixel(x, y)
    except Exception:
        pass

    # Method 2: PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=(x, y, x+1, y+1))
        px = img.getpixel((0, 0))
        return px[0], px[1], px[2]
    except Exception:
        pass

    # Method 3: grim (Wayland native — sway, GNOME, KDE Plasma)
    try:
        tmp = '/tmp/_smacro_px.png'
        ret = subprocess.call(
            ['grim', '-g', f'{x},{y} 1x1', tmp],
            stderr=subprocess.DEVNULL
        )
        if ret == 0:
            from PIL import Image
            img = Image.open(tmp)
            px = img.getpixel((0, 0))
            try: os.unlink(tmp)
            except: pass
            return px[0], px[1], px[2]
    except Exception:
        pass

    # Method 4: GNOME Shell D-Bus ekran görüntüsü (GNOME Wayland)
    try:
        tmp = '/tmp/_smacro_px.png'
        ret = subprocess.call([
            'gdbus', 'call', '--session',
            '--dest', 'org.gnome.Shell.Screenshot',
            '--object-path', '/org/gnome/Shell/Screenshot',
            '--method', 'org.gnome.Shell.Screenshot.ScreenshotArea',
            str(x), str(y), '1', '1', 'false', tmp
        ], stderr=subprocess.DEVNULL)
        if ret == 0:
            from PIL import Image
            img = Image.open(tmp)
            px = img.getpixel((0, 0))
            try: os.unlink(tmp)
            except: pass
            return px[0], px[1], px[2]
    except Exception:
        pass

    return None


def _get_all_windows():
    if HAS_PYGETWINDOW:
        try:
            return [w.title for w in gw.getAllWindows() if w.title.strip()]
        except:
            return []
    try:
        out = subprocess.check_output(['wmctrl', '-l'], stderr=subprocess.DEVNULL).decode()
        wins = []
        for line in out.strip().split('\n'):
            parts = line.split(None, 3)
            if len(parts) >= 4 and parts[3].strip():
                wins.append(parts[3].strip())
        return list(dict.fromkeys(wins))  # deduplicate, preserve order
    except:
        return []


def _get_window_rect(title):
    if HAS_PYGETWINDOW:
        try:
            return gw.getWindowsWithTitle(title)[0]
        except:
            return None
    try:
        win_ids = subprocess.check_output(
            ['xdotool', 'search', '--name', title],
            stderr=subprocess.DEVNULL
        ).decode().strip().split('\n')
        if not win_ids or not win_ids[0]:
            return None
        out = subprocess.check_output(
            ['xdotool', 'getwindowgeometry', win_ids[0]],
            stderr=subprocess.DEVNULL
        ).decode()
        pos_line = next(l for l in out.split('\n') if 'Position' in l)
        pos_str = pos_line.split(':')[1].strip().split(' ')[0]
        x, y = map(int, pos_str.split(','))
        return _WinRect(x, y)
    except:
        return None


def _activate_window(title):
    if HAS_PYGETWINDOW:
        try:
            gw.getWindowsWithTitle(title)[0].activate()
        except:
            pass
    else:
        try:
            subprocess.call(['wmctrl', '-a', title], stderr=subprocess.DEVNULL)
        except:
            pass


class ShadowMacroV8:
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowMacro V8.2 - Linux")
        self.root.geometry("1000x750")

        # --- RENKLER ---
        self.colors = {
            "bg": "#2b2b2b",
            "panel": "#333333",
            "fg": "#eeeeee",
            "accent": "#61afef",
            "success": "#98c379",
            "danger": "#e06c75",
            "warning": "#e5c07b",
            "input": "#424242"
        }
        self.root.configure(bg=self.colors["bg"])

        # --- DEĞİŞKENLER ---
        self.is_macro_running = False
        self.is_f7_running = False
        self.is_recording = False
        self.is_picking = False

        self.actions = []
        self.loop_count = tk.IntVar(value=0)
        self.human_speed = tk.BooleanVar(value=True)
        self.use_turbo_mode = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)
        self.use_window_mode = tk.BooleanVar(value=False)
        self.target_window_title = tk.StringVar()

        self.f7_cps = tk.DoubleVar(value=10.0)
        self.manual_type = tk.StringVar(value="Click")
        self.temp_x = tk.IntVar(value=0)
        self.temp_y = tk.IntVar(value=0)
        self.picked_color = tk.StringVar(value="")

        self.input_widgets = {}

        self.mouse_listener = None

        self.setup_styles()
        self.create_gui()
        self.load_config()
        self.start_hotkey_listener()

        self.picker_listener = keyboard.Listener(on_release=self.on_picker_key)
        self.picker_listener.start()
        self.refresh_windows()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 10))
        style.configure("TButton", background="#3e4451", foreground="white", borderwidth=0, font=("Segoe UI", 9))
        style.map("TButton", background=[("active", self.colors["accent"])])

        style.configure("Treeview",
                        background=self.colors["input"],
                        foreground="white",
                        fieldbackground=self.colors["input"],
                        font=("Consolas", 10),
                        rowheight=28,
                        borderwidth=0,
                        highlightthickness=0)
        style.configure("Treeview.Heading", background="#21252b", foreground="#abb2bf", font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", self.colors["accent"])])

    def create_gui(self):
        # --- ÜST PANEL ---
        header = tk.Frame(self.root, bg=self.colors["panel"], pady=15, padx=20)
        header.pack(fill="x")

        tk.Label(header, text="SHADOW MACRO V8.2", font=("Segoe UI", 16, "bold"), fg=self.colors["accent"], bg=self.colors["panel"]).pack(side="left")

        win_frame = tk.Frame(header, bg=self.colors["panel"])
        win_frame.pack(side="right")

        self.cb_window = ttk.Combobox(win_frame, textvariable=self.target_window_title, width=25, state="readonly")
        self.cb_window.pack(side="left", padx=5)
        tk.Button(win_frame, text="🔄", width=3, bg="#444", fg="white", command=self.refresh_windows).pack(side="left")

        chk_win = tk.Checkbutton(win_frame, text="Pencere Modu", variable=self.use_window_mode, bg=self.colors["panel"], fg="white", selectcolor="#222", activebackground=self.colors["panel"])
        chk_win.pack(side="left", padx=10)

        chk_top = tk.Checkbutton(win_frame, text="Sabitle", variable=self.always_on_top, command=self.toggle_always_on_top, bg=self.colors["panel"], fg="white", selectcolor="#222", activebackground=self.colors["panel"])
        chk_top.pack(side="left")

        # --- ORTA BÖLÜM ---
        content = tk.Frame(self.root, bg=self.colors["bg"], padx=15, pady=15)
        content.pack(fill="both", expand=True)

        # === SOL TARAF ===
        left_frame = tk.Frame(content, bg=self.colors["bg"])
        left_frame.pack(side="left", fill="both", expand=True)

        list_container = tk.Frame(left_frame, bg=self.colors["input"])
        list_container.pack(side="top", fill="both", expand=True)

        scroll = tk.Scrollbar(list_container, orient="vertical")
        scroll.pack(side="right", fill="y")

        cols = ("ID", "Type", "Detail", "Delay")
        self.tree = ttk.Treeview(list_container, columns=cols, show='headings', selectmode="browse", yscrollcommand=scroll.set)

        self.tree.heading("ID", text="#"); self.tree.column("ID", width=40, anchor="center")
        self.tree.heading("Type", text="İşlem"); self.tree.column("Type", width=90)
        self.tree.heading("Detail", text="Detaylar"); self.tree.column("Detail", width=250)
        self.tree.heading("Delay", text="Süre"); self.tree.column("Delay", width=70, anchor="center")

        self.tree.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.tree.yview)

        btn_bar = tk.Frame(left_frame, bg=self.colors["bg"], pady=10)
        btn_bar.pack(side="bottom", fill="x")

        tk.Button(btn_bar, text="▲", width=3, bg="#444", fg="white", command=lambda: self.move_row(-1)).pack(side="left", padx=1)
        tk.Button(btn_bar, text="▼", width=3, bg="#444", fg="white", command=lambda: self.move_row(1)).pack(side="left", padx=1)
        tk.Button(btn_bar, text="Sil", bg=self.colors["danger"], fg="white", width=6, command=self.delete_row).pack(side="left", padx=10)
        tk.Button(btn_bar, text="Temizle", bg="#444", fg="white", width=8, command=lambda: [self.actions.clear(), self.refresh_tree()]).pack(side="left")

        tk.Button(btn_bar, text="💾 Kaydet", bg="#555", fg="white", command=self.save_project).pack(side="right", padx=2)
        tk.Button(btn_bar, text="📂 Aç", bg="#555", fg="white", command=self.load_project).pack(side="right", padx=2)

        # === SAĞ TARAF: EDİTÖR ===
        right_frame = tk.LabelFrame(content, text=" DETAYLI EDİTÖR ", bg=self.colors["panel"], fg="#888", font=("Segoe UI", 9, "bold"), width=320)
        right_frame.pack(side="right", fill="y", padx=(15, 0))
        right_frame.pack_propagate(False)

        form = tk.Frame(right_frame, bg=self.colors["panel"], padx=10, pady=10)
        form.pack(fill="x")

        tk.Label(form, text="İşlem Tipi:", bg=self.colors["panel"]).pack(anchor="w")
        self.cb_type = ttk.Combobox(form, textvariable=self.manual_type, values=["Click", "Press", "Scroll", "WaitColor"], state="readonly")
        self.cb_type.pack(fill="x", pady=(2, 10))
        self.cb_type.bind("<<ComboboxSelected>>", self.update_editor_ui)

        self.dynamic_frame = tk.Frame(form, bg=self.colors["panel"])
        self.dynamic_frame.pack(fill="x")

        self.btn_pick = tk.Button(form, text="🎯 Konum Seç (X Tuşu)", bg=self.colors["warning"], fg="#222", font=("Segoe UI", 9, "bold"), command=lambda: self.start_picker("loc"))

        tk.Label(form, text="Bekleme / Timeout (sn):", bg=self.colors["panel"]).pack(anchor="w", pady=(10, 0))
        self.ent_delay = tk.Entry(form, bg=self.colors["input"], fg="white", relief="flat", insertbackground="white")
        self.ent_delay.insert(0, "0.1")
        self.ent_delay.pack(fill="x", pady=2, ipady=3)

        tk.Button(form, text="➕ Listeye Ekle", bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), pady=5, command=self.add_manual_action).pack(fill="x", pady=20)

        self.btn_rec = tk.Button(right_frame, text="🔴 CANLI KAYIT MODU", bg=self.colors["danger"], fg="white", font=("Segoe UI", 10, "bold"), pady=8, command=self.toggle_recording)
        self.btn_rec.pack(side="bottom", fill="x", padx=10, pady=10)

        # --- ALT PANEL ---
        footer = tk.Frame(self.root, bg="#21252b", pady=15, padx=20)
        footer.pack(fill="x", side="bottom")

        f7_box = tk.Frame(footer, bg="#21252b")
        f7_box.pack(side="left")

        tk.Label(f7_box, text="F7 CLICKER", fg=self.colors["warning"], bg="#21252b", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        f7_inner = tk.Frame(f7_box, bg="#21252b")
        f7_inner.pack(fill="x")

        tk.Label(f7_inner, text="Hız:", bg="#21252b", fg="#aaa").pack(side="left")
        tk.Scale(f7_inner, from_=1, to=60, orient="horizontal", variable=self.f7_cps, bg="#21252b", fg=self.colors["accent"], length=100, highlightthickness=0).pack(side="left", padx=5)
        self.lbl_f7_status = tk.Label(f7_inner, text="DURDU", fg="#555", bg="#21252b", width=8)
        self.lbl_f7_status.pack(side="left")

        f6_box = tk.Frame(footer, bg="#21252b")
        f6_box.pack(side="right")

        opts = tk.Frame(f6_box, bg="#21252b")
        opts.pack(side="top", anchor="e", pady=(0, 5))

        tk.Label(opts, text="Tekrar:", bg="#21252b", fg="#aaa").pack(side="left")
        tk.Entry(opts, textvariable=self.loop_count, width=4, bg=self.colors["input"], fg="white", relief="flat").pack(side="left", padx=5)

        tk.Checkbutton(opts, text="Turbo", variable=self.use_turbo_mode, bg="#21252b", fg="white", selectcolor="#222", activebackground="#21252b").pack(side="left", padx=5)
        tk.Checkbutton(opts, text="Anti-Bot", variable=self.human_speed, bg="#21252b", fg="white", selectcolor="#222", activebackground="#21252b").pack(side="left")

        self.btn_play = tk.Button(f6_box, text="▶ MAKROYU BAŞLAT (F6)", bg=self.colors["accent"], fg="white", font=("Segoe UI", 11, "bold"), width=25, command=self.start_macro_thread)
        self.btn_play.pack(side="bottom")

        self.update_editor_ui(None)

    # --- PENCERE YÖNETİMİ ---
    def refresh_windows(self):
        try:
            wins = _get_all_windows()
            self.cb_window['values'] = sorted(wins)
            if wins: self.cb_window.current(0)
        except:
            pass

    def get_window_rect(self):
        title = self.target_window_title.get()
        if not title:
            return None
        return _get_window_rect(title)

    # --- EDİTÖR UI ---
    def update_editor_ui(self, event):
        for widget in self.dynamic_frame.winfo_children(): widget.destroy()
        self.btn_pick.pack_forget()
        atype = self.manual_type.get()
        bg_col = self.colors["panel"]

        if atype == "Click":
            row = tk.Frame(self.dynamic_frame, bg=bg_col); row.pack(fill="x", pady=5)
            tk.Label(row, text="X:", bg=bg_col).pack(side="left")
            self.input_widgets["x"] = tk.Entry(row, textvariable=self.temp_x, width=8, bg=self.colors["input"], fg="white", relief="flat"); self.input_widgets["x"].pack(side="left", padx=5)
            tk.Label(row, text="Y:", bg=bg_col).pack(side="left")
            self.input_widgets["y"] = tk.Entry(row, textvariable=self.temp_y, width=8, bg=self.colors["input"], fg="white", relief="flat"); self.input_widgets["y"].pack(side="left", padx=5)
            self.btn_pick.config(text="🎯 Konum Seç (X)", command=lambda: self.start_picker("loc"), bg=self.colors["warning"])
            self.btn_pick.pack(fill="x", pady=10, in_=self.dynamic_frame.master)
        elif atype == "WaitColor":
            tk.Label(self.dynamic_frame, text="Renk (R,G,B):", bg=bg_col).pack(anchor="w")
            self.input_widgets["color"] = tk.Entry(self.dynamic_frame, textvariable=self.picked_color, bg=self.colors["input"], fg="white", relief="flat"); self.input_widgets["color"].pack(fill="x", pady=2)
            row = tk.Frame(self.dynamic_frame, bg=bg_col); row.pack(fill="x", pady=5)
            tk.Label(row, text="X:", bg=bg_col).pack(side="left")
            self.input_widgets["x"] = tk.Entry(row, textvariable=self.temp_x, width=8, bg=self.colors["input"], fg="white", relief="flat"); self.input_widgets["x"].pack(side="left", padx=5)
            tk.Label(row, text="Y:", bg=bg_col).pack(side="left")
            self.input_widgets["y"] = tk.Entry(row, textvariable=self.temp_y, width=8, bg=self.colors["input"], fg="white", relief="flat"); self.input_widgets["y"].pack(side="left", padx=5)
            self.btn_pick.config(text="👁️ Renk & Konum (C)", command=lambda: self.start_picker("color"), bg=self.colors["accent"])
            self.btn_pick.pack(fill="x", pady=10, in_=self.dynamic_frame.master)
        elif atype == "Press":
            tk.Label(self.dynamic_frame, text="Tuş (a, enter):", bg=bg_col).pack(anchor="w")
            self.input_widgets["key"] = tk.Entry(self.dynamic_frame, bg=self.colors["input"], fg="white", relief="flat"); self.input_widgets["key"].pack(fill="x", pady=5)
        elif atype == "Scroll":
            tk.Label(self.dynamic_frame, text="Miktar (+/-):", bg=bg_col).pack(anchor="w")
            self.input_widgets["amount"] = tk.Entry(self.dynamic_frame, bg=self.colors["input"], fg="white", relief="flat"); self.input_widgets["amount"].insert(0, "-100"); self.input_widgets["amount"].pack(fill="x", pady=5)

    def start_picker(self, mode):
        self.is_picking = mode
        msg = "Mouse ile git ve 'X' bas..." if mode == "loc" else "Mouse ile git ve 'C' bas..."
        self.btn_pick.config(text=msg, bg="#98c379")

    def on_picker_key(self, key):
        if not self.is_picking: return
        if not isinstance(key, KeyCode) or not key.char: return
        ch = key.char.lower()

        if self.is_picking == "loc" and ch == 'x':
            x, y = pyautogui.position()
            if self.use_window_mode.get():
                win = self.get_window_rect()
                if win: x -= win.left; y -= win.top
            self.temp_x.set(x); self.temp_y.set(y)
            self.stop_picker()

        elif self.is_picking == "color" and ch == 'c':
            x, y = pyautogui.position()
            pixel = _get_pixel(x, y)
            if pixel is None:
                self.is_picking = False
                self.root.after(0, lambda: self.btn_pick.config(
                    text="❌ Renk alınamadı!", bg=self.colors["danger"]))
                self.root.after(0, lambda: messagebox.showerror(
                    "Wayland Renk Hatası",
                    "Ekran pikseli okunamadı.\n\n"
                    "Çözüm 1 (Fedora/Nobara):\n"
                    "  sudo dnf install gnome-screenshot grim\n\n"
                    "Çözüm 2: Oturumu 'GNOME on Xorg' ile aç."
                ))
                self.root.after(2500, lambda: self.update_editor_ui(None))
                return
            r, g, b = pixel
            if self.use_window_mode.get():
                win = self.get_window_rect()
                if win: x -= win.left; y -= win.top
            self.temp_x.set(x); self.temp_y.set(y)
            self.picked_color.set(f"{r},{g},{b}")
            self.stop_picker()

    def stop_picker(self):
        self.is_picking = False
        self.root.after(0, lambda: self.btn_pick.config(text="✅ Seçim Alındı!", bg=self.colors["panel"]))
        self.root.after(1000, lambda: self.update_editor_ui(None))

    # --- ÇALIŞTIRMA ---
    def start_hotkey_listener(self):
        def on_press(key):
            if key == Key.f6: self.toggle_macro()
            elif key == Key.f7: self.toggle_f7_clicker()
        threading.Thread(target=lambda: keyboard.Listener(on_press=on_press).start(), daemon=True).start()

    def toggle_macro(self):
        if self.is_macro_running:
            self.is_macro_running = False
            self.btn_play.config(text="▶ MAKROYU BAŞLAT (F6)", bg=self.colors["accent"])
        else:
            self.start_macro_thread()

    def start_macro_thread(self):
        if not self.actions: return
        self.is_macro_running = True
        self.btn_play.config(text="⏹ ÇALIŞIYOR (F6 DURDUR)", bg=self.colors["danger"])
        threading.Thread(target=self.run_macro, daemon=True).start()

    def run_macro(self):
        loops = self.loop_count.get()
        cnt = 0
        if self.use_window_mode.get():
            title = self.target_window_title.get()
            if title:
                _activate_window(title)

        while self.is_macro_running:
            if loops > 0 and cnt >= loops: break
            win_off_x, win_off_y = 0, 0
            if self.use_window_mode.get():
                win = self.get_window_rect()
                if win: win_off_x, win_off_y = win.left, win.top

            for act in self.actions:
                if not self.is_macro_running: break
                if act["type"] == "WaitColor":
                    trgb = tuple(map(int, act["color"].split(',')))
                    cx, cy = act["x"] + win_off_x, act["y"] + win_off_y
                    start_t = time.time()
                    found = False
                    while time.time() - start_t < act["delay"]:
                        if not self.is_macro_running: break
                        if pyautogui.pixelMatchesColor(cx, cy, trgb, tolerance=10): found = True; break
                        time.sleep(0.1)
                    if not found: continue
                elif act["delay"] > 0:
                    d = act["delay"]
                    if self.human_speed.get() and not self.use_turbo_mode.get(): d *= random.uniform(0.8, 1.2)
                    time.sleep(d)

                try:
                    if act["type"] == "Click":
                        tx, ty = act["x"] + win_off_x, act["y"] + win_off_y
                        if self.use_turbo_mode.get():
                            _turbo_click(tx, ty)
                        else:
                            if self.human_speed.get(): tx += random.randint(-2, 2); ty += random.randint(-2, 2)
                            pyautogui.click(tx, ty)
                    elif act["type"] == "Press": pyautogui.press(act["key"])
                    elif act["type"] == "Scroll": pyautogui.scroll(act["amount"])
                except:
                    pass
            cnt += 1
        self.is_macro_running = False
        self.btn_play.config(text="▶ MAKROYU BAŞLAT (F6)", bg=self.colors["accent"])

    def toggle_f7_clicker(self):
        if self.is_f7_running:
            self.is_f7_running = False
            self.lbl_f7_status.config(text="DURDU", fg="#555")
        else:
            self.is_f7_running = True
            self.lbl_f7_status.config(text="AKTİF", fg=self.colors["warning"])
            threading.Thread(target=self.run_f7, daemon=True).start()

    def run_f7(self):
        while self.is_f7_running:
            try:
                if self.use_turbo_mode.get():
                    _turbo_click()
                    time.sleep(1.0 / self.f7_cps.get())
                else:
                    pyautogui.click()
                    time.sleep((1.0 / self.f7_cps.get()) * random.uniform(0.9, 1.1))
            except:
                pass

    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.btn_rec.config(text="🔴 CANLI KAYIT MODU", bg=self.colors["danger"])
            if self.mouse_listener: self.mouse_listener.stop()
        else:
            self.is_recording = True
            self.btn_rec.config(text="⏹ BİTİR (ESC)", bg="#444")
            self.actions = []
            self.refresh_tree()
            self.start_rec_time = time.time()
            self.mouse_listener = mouse.Listener(on_click=self.on_record_click)
            self.mouse_listener.start()
            threading.Thread(target=self.esc_watcher, daemon=True).start()

    def esc_watcher(self):
        def on_rel(key):
            if key == Key.esc: self.toggle_recording(); return False
        with keyboard.Listener(on_release=on_rel) as l: l.join()

    def on_record_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            delay = round(time.time() - self.start_rec_time, 2)
            self.start_rec_time = time.time()
            if self.use_window_mode.get():
                win = self.get_window_rect()
                if win: x -= win.left; y -= win.top
            self.actions.append({"type": "Click", "x": x, "y": y, "delay": delay})
            self.root.after(0, self.refresh_tree)

    def add_manual_action(self):
        try:
            atype = self.manual_type.get()
            delay = float(self.ent_delay.get())
            act = {"type": atype, "delay": delay}
            if atype == "Click": act["x"] = self.temp_x.get(); act["y"] = self.temp_y.get()
            elif atype == "WaitColor": act["x"] = self.temp_x.get(); act["y"] = self.temp_y.get(); act["color"] = self.picked_color.get()
            elif atype == "Press": act["key"] = self.input_widgets["key"].get()
            elif atype == "Scroll": act["amount"] = int(self.input_widgets["amount"].get())
            self.actions.append(act); self.refresh_tree()
        except:
            messagebox.showerror("Hata", "Değerleri kontrol et.")

    def refresh_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for i, a in enumerate(self.actions):
            det = ""
            if a["type"] == "Click": det = f"Pos: {a['x']},{a['y']}"
            elif a["type"] == "WaitColor": det = f"Color: {a['color']} @ {a['x']},{a['y']}"
            elif a["type"] == "Press": det = f"Key: {a['key']}"
            self.tree.insert("", "end", values=(i+1, a["type"], det, a["delay"]))

    def delete_row(self):
        sel = self.tree.selection()
        if sel: del self.actions[self.tree.index(sel[0])]; self.refresh_tree()

    def move_row(self, d):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0]); n = idx + d
        if 0 <= n < len(self.actions):
            self.actions[idx], self.actions[n] = self.actions[n], self.actions[idx]
            self.refresh_tree(); self.tree.selection_set(self.tree.get_children()[n])

    def save_project(self):
        f = filedialog.asksaveasfilename(defaultextension=".json")
        if f:
            with open(f, 'w') as file: json.dump(self.actions, file)

    def load_project(self):
        f = filedialog.askopenfilename()
        if f:
            with open(f, 'r') as file: self.actions = json.load(file); self.refresh_tree()

    def load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json") as f:
                    d = json.load(f)
                    self.f7_cps.set(d.get("f7", 10))
                    self.use_turbo_mode.set(d.get("turbo", False))
                    self.always_on_top.set(d.get("top", False))
                    self.toggle_always_on_top()
            except:
                pass

    def save_config(self):
        d = {"f7": self.f7_cps.get(), "turbo": self.use_turbo_mode.get(), "top": self.always_on_top.get()}
        with open("config.json", "w") as f: json.dump(d, f)

    def toggle_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    def on_close(self):
        self.save_config(); self.root.destroy(); os._exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = ShadowMacroV8(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

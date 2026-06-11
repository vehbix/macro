#!/usr/bin/env python3
"""
ShadowMacro V9 — Modern UI + gerçek arka plan tıklama (XTEST)

Yenilikler (V8'e göre):
  * "Pencere Modu — Klavye Sinyali": Hedef pencereye XTEST ile tuş (varsayılan
    Enter) gönderir. MOUSE HİÇ KULLANILMAZ. Wayland + Proton/Wine altında
    çalışır (XSendEvent Wine tarafından yok sayıldığı için XTEST kullanıyoruz).
  * "Pencere Modu — İmleç Işınla": Koordinata tıklamak için imleci kısa süre
    hedefe ışınlar, tıklar, anında geri getirir (XTEST warp-click).
  * customtkinter ile yeniden tasarlanmış modern, koyu arayüz.
"""

import os
import time
import json
import random
import platform
import threading
import subprocess

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import customtkinter as ctk

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    HAS_PYAUTOGUI = True
except Exception:
    HAS_PYAUTOGUI = False

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

IS_WINDOWS = platform.system() == "Windows"

# --- X11 / XTEST backend (Linux / XWayland) ---
HAS_X11 = False
if not IS_WINDOWS:
    try:
        from Xlib import display as Xdisplay, X, XK
        from Xlib.ext import xtest
        HAS_X11 = True
    except Exception:
        HAS_X11 = False

# Kullanıcı dostu tuş adı -> X keysym adı eşlemesi
_KEYSYM_ALIAS = {
    "enter": "Return", "return": "Return", "space": "space", "spacebar": "space",
    "tab": "Tab", "esc": "Escape", "escape": "Escape", "backspace": "BackSpace",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "shift": "Shift_L", "ctrl": "Control_L", "alt": "Alt_L",
}


def list_windows():
    """[(baslik, wid_int), ...] — wmctrl ile."""
    if IS_WINDOWS:
        return []
    try:
        out = subprocess.check_output(["wmctrl", "-l"],
                                      stderr=subprocess.DEVNULL).decode()
    except Exception:
        return []
    res = []
    for line in out.strip().split("\n"):
        parts = line.split(None, 3)
        if len(parts) >= 4 and parts[3].strip():
            try:
                wid = int(parts[0], 16)
            except ValueError:
                continue
            res.append((parts[3].strip(), wid))
    # aynı başlığı tekrar etme
    seen, uniq = set(), []
    for t, w in res:
        if t not in seen:
            seen.add(t)
            uniq.append((t, w))
    return uniq


class X11Backend:
    """Tek bir thread içinde açılıp kullanılmalı (python-xlib thread-safe değil)."""

    def __init__(self):
        self.d = Xdisplay.Display()
        self.root = self.d.screen().root

    def close(self):
        try:
            self.d.close()
        except Exception:
            pass

    def focus_window(self, wid):
        try:
            subprocess.call(["wmctrl", "-i", "-a", hex(wid)],
                            stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _keycode(self, keyname):
        if not keyname:
            return 0
        name = _KEYSYM_ALIAS.get(keyname.strip().lower(), keyname.strip())
        ks = XK.string_to_keysym(name)
        if ks == 0 and len(name) == 1:
            ks = XK.string_to_keysym(name.lower())
        if ks == 0:
            ks = XK.string_to_keysym(name.capitalize())
        return self.d.keysym_to_keycode(ks) if ks else 0

    def send_key(self, keyname, hold=0.012):
        """Tuşa bas, kısa süre tut, bırak. Tutma süresi olmadan oyun çoğu
        zaman 0ms'lik basışı yakalayamaz (kare başına örnekleme)."""
        kc = self._keycode(keyname)
        if not kc:
            return False
        xtest.fake_input(self.d, X.KeyPress, kc)
        self.d.sync()
        if hold:
            time.sleep(hold)
        xtest.fake_input(self.d, X.KeyRelease, kc)
        self.d.sync()
        return True

    def is_active(self, wid):
        """Hedef pencere şu an aktif (odaklı) pencere mi?"""
        try:
            NET_ACTIVE = self.d.intern_atom("_NET_ACTIVE_WINDOW")
            prop = self.root.get_full_property(NET_ACTIVE, X.AnyPropertyType)
            return bool(prop) and prop.value[0] == wid
        except Exception:
            return False

    def abs_origin(self, wid):
        """Pencerenin (0,0) noktasının mutlak ekran koordinatı."""
        try:
            trans = self.root.translate_coords(wid, 0, 0)
            return (-trans.x, -trans.y)
        except Exception:
            return (0, 0)

    def warp_click(self, ax, ay, restore=True):
        try:
            p = self.root.query_pointer()
            ox, oy = p.root_x, p.root_y
        except Exception:
            ox = oy = None
        xtest.fake_input(self.d, X.MotionNotify, x=int(ax), y=int(ay))
        self.d.sync()
        xtest.fake_input(self.d, X.ButtonPress, 1)
        self.d.sync()
        xtest.fake_input(self.d, X.ButtonRelease, 1)
        self.d.sync()
        if restore and ox is not None:
            xtest.fake_input(self.d, X.MotionNotify, x=ox, y=oy)
            self.d.sync()


# ---------------------------------------------------------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT = "#5b8cff"
ACCENT_HOVER = "#4a76e0"
SUCCESS = "#3ecf8e"
SUCCESS_HOVER = "#34b87c"
DANGER = "#ff5c5c"
DANGER_HOVER = "#e04848"
WARN = "#f5b14c"
CARD = "#1c2230"
CARD2 = "#232a3a"
BG = "#141821"
MUTED = "#8a93a6"
FG = "#e8ecf4"


class ShadowMacroV9:
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowMacro V9")
        self.root.geometry("1080x760")
        self.root.minsize(960, 680)
        self.root.configure(fg_color=BG)

        # durum
        self.is_macro_running = False
        self.is_clicker_running = False
        self.is_recording = False
        self.is_picking = False

        self.actions = []
        self.windows_map = {}          # baslik -> wid

        # değişkenler
        self.loop_count = tk.IntVar(value=0)
        self.human_speed = tk.BooleanVar(value=True)
        self.use_window_mode = tk.BooleanVar(value=True)
        self.click_method = tk.StringVar(value="Klavye Sinyali")  # veya "İmleç Işınla"
        self.signal_key = tk.StringVar(value="Enter")
        self.target_window_title = tk.StringVar()
        self.always_on_top = tk.BooleanVar(value=False)

        self.cps = tk.DoubleVar(value=15.0)
        self.manual_type = tk.StringVar(value="Click")
        self.temp_x = tk.IntVar(value=0)
        self.temp_y = tk.IntVar(value=0)
        self.picked_color = tk.StringVar(value="")
        self.ent_delay_var = tk.StringVar(value="0.1")

        self.input_widgets = {}

        self._build_styles()
        self._build_ui()
        self._load_config()
        self._start_hotkeys()

        self.picker_listener = keyboard.Listener(on_release=self._on_picker_key)
        self.picker_listener.start()
        self.refresh_windows()

    # ---------------- stiller ----------------
    def _build_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Modern.Treeview",
                        background=CARD2, foreground=FG,
                        fieldbackground=CARD2, borderwidth=0,
                        rowheight=30, font=("Segoe UI", 10))
        style.configure("Modern.Treeview.Heading",
                        background=CARD, foreground=MUTED,
                        relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Modern.Treeview.Heading",
                  background=[("active", CARD)])
        style.map("Modern.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])

    # ---------------- UI ----------------
    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14, **kw)

    def _build_ui(self):
        root = self.root
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # ===== ÜST BAR =====
        header = ctk.CTkFrame(root, fg_color=CARD, corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=22, pady=14, sticky="w")
        ctk.CTkLabel(title_box, text="⚡ ShadowMacro",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     text_color=FG).pack(side="left")
        ctk.CTkLabel(title_box, text="V9",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=ACCENT).pack(side="left", padx=(8, 0), pady=(6, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=2, padx=18, sticky="e")
        ctk.CTkSwitch(right, text="Üstte sabit",
                      variable=self.always_on_top,
                      command=self._toggle_top,
                      progress_color=ACCENT).pack(side="left", padx=8)

        # ===== HEDEF PENCERE + MOD ŞERİDİ =====
        body = ctk.CTkScrollableFrame(root, fg_color=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(14, 6))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        target = self._card(body)
        target.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        target.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(target, text="🎯 Hedef Pencere",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=FG).grid(row=0, column=0, padx=18, pady=(16, 4), sticky="w")

        self.cb_window = ctk.CTkComboBox(target, variable=self.target_window_title,
                                         values=[], width=360,
                                         button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                                         border_color=CARD2, dropdown_fg_color=CARD2)
        self.cb_window.grid(row=1, column=0, columnspan=2, padx=18, pady=(0, 6), sticky="ew")
        ctk.CTkButton(target, text="🔄 Yenile", width=90, command=self.refresh_windows,
                      fg_color=CARD2, hover_color="#2c3547").grid(row=1, column=2, padx=(0, 18))

        # mod satırı
        modrow = ctk.CTkFrame(target, fg_color="transparent")
        modrow.grid(row=2, column=0, columnspan=3, padx=18, pady=(6, 16), sticky="ew")

        ctk.CTkSwitch(modrow, text="Pencere Modu",
                      variable=self.use_window_mode,
                      progress_color=SUCCESS,
                      command=self._update_method_ui).pack(side="left")

        self.seg_method = ctk.CTkSegmentedButton(
            modrow, values=["Klavye Sinyali", "İmleç Işınla"],
            variable=self.click_method,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            command=lambda *_: self._update_method_ui())
        self.seg_method.pack(side="left", padx=16)

        self.key_box = ctk.CTkFrame(modrow, fg_color="transparent")
        self.key_box.pack(side="left", padx=6)
        ctk.CTkLabel(self.key_box, text="Tuş:", text_color=MUTED).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(self.key_box, textvariable=self.signal_key, width=90,
                     fg_color=CARD2, border_color=CARD2).pack(side="left")

        self.lbl_mode_hint = ctk.CTkLabel(target, text="", text_color=MUTED,
                                          font=ctk.CTkFont("Segoe UI", 11))
        self.lbl_mode_hint.grid(row=3, column=0, columnspan=3, padx=18, pady=(0, 14), sticky="w")

        # ===== SOL: AKSİYON LİSTESİ =====
        left = self._card(body)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="📋 Aksiyon Listesi",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=FG).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        tree_holder = ctk.CTkFrame(left, fg_color=CARD2, corner_radius=10)
        tree_holder.grid(row=1, column=0, sticky="nsew", padx=14, pady=4)
        tree_holder.grid_rowconfigure(0, weight=1)
        tree_holder.grid_columnconfigure(0, weight=1)

        cols = ("ID", "Type", "Detail", "Delay")
        self.tree = ttk.Treeview(tree_holder, columns=cols, show="headings",
                                 selectmode="browse", style="Modern.Treeview")
        self.tree.heading("ID", text="#"); self.tree.column("ID", width=40, anchor="center")
        self.tree.heading("Type", text="İşlem"); self.tree.column("Type", width=90)
        self.tree.heading("Detail", text="Detay"); self.tree.column("Detail", width=240)
        self.tree.heading("Delay", text="Süre"); self.tree.column("Delay", width=70, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        sb = ttk.Scrollbar(tree_holder, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")

        btnbar = ctk.CTkFrame(left, fg_color="transparent")
        btnbar.grid(row=2, column=0, sticky="ew", padx=14, pady=12)
        for txt, cmd in [("▲", lambda: self.move_row(-1)), ("▼", lambda: self.move_row(1))]:
            ctk.CTkButton(btnbar, text=txt, width=38, command=cmd,
                          fg_color=CARD2, hover_color="#2c3547").pack(side="left", padx=2)
        ctk.CTkButton(btnbar, text="Sil", width=60, command=self.delete_row,
                      fg_color=DANGER, hover_color=DANGER_HOVER).pack(side="left", padx=(10, 2))
        ctk.CTkButton(btnbar, text="Temizle", width=80,
                      command=lambda: [self.actions.clear(), self.refresh_tree()],
                      fg_color=CARD2, hover_color="#2c3547").pack(side="left", padx=2)
        ctk.CTkButton(btnbar, text="📂 Aç", width=64, command=self.load_project,
                      fg_color=CARD2, hover_color="#2c3547").pack(side="right", padx=2)
        ctk.CTkButton(btnbar, text="💾 Kaydet", width=86, command=self.save_project,
                      fg_color=CARD2, hover_color="#2c3547").pack(side="right", padx=2)

        # ===== SAĞ: EDİTÖR =====
        right_card = self._card(body)
        right_card.grid(row=1, column=1, sticky="nsew")
        right_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_card, text="🛠️ Editör",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=FG).grid(row=0, column=0, padx=18, pady=(16, 8), sticky="w")

        ctk.CTkLabel(right_card, text="İşlem tipi", text_color=MUTED).grid(
            row=1, column=0, padx=18, sticky="w")
        self.cb_type = ctk.CTkComboBox(
            right_card, variable=self.manual_type,
            values=["Click", "Press", "Scroll", "WaitColor"],
            command=lambda *_: self._update_editor_ui(),
            button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            border_color=CARD2, dropdown_fg_color=CARD2)
        self.cb_type.grid(row=2, column=0, padx=18, pady=(2, 10), sticky="ew")

        self.dynamic_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        self.dynamic_frame.grid(row=3, column=0, padx=18, sticky="ew")
        self.dynamic_frame.grid_columnconfigure(0, weight=1)

        self.btn_pick = ctk.CTkButton(right_card, text="🎯 Konum Seç (X)",
                                      command=lambda: self.start_picker("loc"),
                                      fg_color=WARN, hover_color="#d99a3a",
                                      text_color="#1a1a1a")
        self.btn_pick.grid(row=4, column=0, padx=18, pady=8, sticky="ew")

        ctk.CTkLabel(right_card, text="Bekleme / Timeout (sn)", text_color=MUTED).grid(
            row=5, column=0, padx=18, pady=(8, 0), sticky="w")
        ctk.CTkEntry(right_card, textvariable=self.ent_delay_var,
                     fg_color=CARD2, border_color=CARD2).grid(
            row=6, column=0, padx=18, pady=(2, 8), sticky="ew")

        ctk.CTkButton(right_card, text="➕ Listeye Ekle",
                      command=self.add_manual_action,
                      fg_color=SUCCESS, hover_color=SUCCESS_HOVER,
                      font=ctk.CTkFont("Segoe UI", 13, "bold"), height=40).grid(
            row=7, column=0, padx=18, pady=(10, 14), sticky="ew")

        self.btn_rec = ctk.CTkButton(right_card, text="🔴 Canlı Kayıt",
                                     command=self.toggle_recording,
                                     fg_color=DANGER, hover_color=DANGER_HOVER,
                                     height=40)
        self.btn_rec.grid(row=8, column=0, padx=18, pady=(0, 16), sticky="ew")

        # ===== ALT BAR: CLICKER + MAKRO =====
        footer = ctk.CTkFrame(root, fg_color=CARD, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)

        # hızlı tıklayıcı
        clicker = ctk.CTkFrame(footer, fg_color="transparent")
        clicker.grid(row=0, column=0, sticky="w", padx=20, pady=14)
        ctk.CTkLabel(clicker, text="HIZLI TIKLAYICI  (F7)",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=WARN).pack(anchor="w")
        crow = ctk.CTkFrame(clicker, fg_color="transparent")
        crow.pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(crow, text="CPS", text_color=MUTED).pack(side="left")
        ctk.CTkSlider(crow, from_=1, to=60, variable=self.cps, width=160,
                      progress_color=ACCENT, button_color=ACCENT,
                      command=lambda v: self.lbl_cps.configure(text=f"{int(float(v))}")).pack(side="left", padx=8)
        self.lbl_cps = ctk.CTkLabel(crow, text="15", width=28, text_color=FG)
        self.lbl_cps.pack(side="left")
        self.btn_clicker = ctk.CTkButton(crow, text="▶ Başlat", width=90,
                                         command=self.toggle_clicker,
                                         fg_color=WARN, hover_color="#d99a3a",
                                         text_color="#1a1a1a")
        self.btn_clicker.pack(side="left", padx=12)
        self.lbl_clicker = ctk.CTkLabel(crow, text="DURDU", text_color=MUTED, width=60)
        self.lbl_clicker.pack(side="left")

        # makro çalıştır
        mac = ctk.CTkFrame(footer, fg_color="transparent")
        mac.grid(row=0, column=1, sticky="e", padx=20, pady=14)
        opts = ctk.CTkFrame(mac, fg_color="transparent")
        opts.pack(anchor="e")
        ctk.CTkLabel(opts, text="Tekrar", text_color=MUTED).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(opts, textvariable=self.loop_count, width=50,
                     fg_color=CARD2, border_color=CARD2).pack(side="left", padx=4)
        ctk.CTkCheckBox(opts, text="İnsansı", variable=self.human_speed,
                        fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(side="left", padx=10)
        self.btn_play = ctk.CTkButton(mac, text="▶ MAKROYU BAŞLAT  (F6)",
                                      command=self.toggle_macro,
                                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                      font=ctk.CTkFont("Segoe UI", 13, "bold"),
                                      height=44, width=260)
        self.btn_play.pack(anchor="e", pady=(8, 0))

        self._update_method_ui()
        self._update_editor_ui()

    # ---------------- mod / editör UI ----------------
    def _update_method_ui(self):
        win = self.use_window_mode.get()
        method = self.click_method.get()
        if win:
            self.seg_method.configure(state="normal")
        else:
            self.seg_method.configure(state="disabled")

        # tuş kutusu sadece Klavye Sinyali modunda
        if win and method == "Klavye Sinyali":
            self.key_box.pack(side="left", padx=6)
        else:
            self.key_box.pack_forget()

        if not win:
            hint = "Normal mod: gerçek fareyle tıklar (pyautogui)."
        elif method == "Klavye Sinyali":
            hint = ("✅ Mouse KULLANILMAZ. Hedef pencere odaklanır ve '"
                    + (self.signal_key.get() or "Enter")
                    + "' tuşu XTEST ile gönderilir. (Wayland + Proton uyumlu)")
        else:
            hint = ("⚠️ İmleç her tıklamada hedefe ışınlanıp geri döner — "
                    "fare kısa süre kıpırdar. Koordinata tıklamak için kullan.")
        self.lbl_mode_hint.configure(text=hint)
        if not HAS_X11 and win:
            self.lbl_mode_hint.configure(
                text="❌ python-xlib bulunamadı — pencere modu çalışmaz.",
                text_color=DANGER)
        else:
            self.lbl_mode_hint.configure(text_color=MUTED)

    def _update_editor_ui(self):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()
        self.btn_pick.grid_remove()
        atype = self.manual_type.get()

        def coord_row():
            row = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text="X", text_color=MUTED).pack(side="left")
            self.input_widgets["x"] = ctk.CTkEntry(row, textvariable=self.temp_x, width=70,
                                                   fg_color=CARD2, border_color=CARD2)
            self.input_widgets["x"].pack(side="left", padx=6)
            ctk.CTkLabel(row, text="Y", text_color=MUTED).pack(side="left")
            self.input_widgets["y"] = ctk.CTkEntry(row, textvariable=self.temp_y, width=70,
                                                   fg_color=CARD2, border_color=CARD2)
            self.input_widgets["y"].pack(side="left", padx=6)

        if atype == "Click":
            coord_row()
            self.btn_pick.configure(text="🎯 Konum Seç (X)",
                                    command=lambda: self.start_picker("loc"),
                                    fg_color=WARN)
            self.btn_pick.grid()
        elif atype == "WaitColor":
            ctk.CTkLabel(self.dynamic_frame, text="Renk (R,G,B)",
                         text_color=MUTED).pack(anchor="w")
            self.input_widgets["color"] = ctk.CTkEntry(
                self.dynamic_frame, textvariable=self.picked_color,
                fg_color=CARD2, border_color=CARD2)
            self.input_widgets["color"].pack(fill="x", pady=2)
            coord_row()
            self.btn_pick.configure(text="👁️ Renk & Konum (C)",
                                    command=lambda: self.start_picker("color"),
                                    fg_color=ACCENT)
            self.btn_pick.grid()
        elif atype == "Press":
            ctk.CTkLabel(self.dynamic_frame, text="Tuş (a, enter, space)",
                         text_color=MUTED).pack(anchor="w")
            self.input_widgets["key"] = ctk.CTkEntry(self.dynamic_frame,
                                                     fg_color=CARD2, border_color=CARD2)
            self.input_widgets["key"].pack(fill="x", pady=4)
        elif atype == "Scroll":
            ctk.CTkLabel(self.dynamic_frame, text="Miktar (+/-)",
                         text_color=MUTED).pack(anchor="w")
            self.input_widgets["amount"] = ctk.CTkEntry(self.dynamic_frame,
                                                       fg_color=CARD2, border_color=CARD2)
            self.input_widgets["amount"].insert(0, "-100")
            self.input_widgets["amount"].pack(fill="x", pady=4)

    # ---------------- pencere yönetimi ----------------
    def refresh_windows(self):
        wins = list_windows()
        self.windows_map = {t: w for t, w in wins}
        titles = sorted(self.windows_map.keys())
        self.cb_window.configure(values=titles)
        if titles and not self.target_window_title.get():
            self.target_window_title.set(titles[0])

    def _target_wid(self):
        return self.windows_map.get(self.target_window_title.get())

    # ---------------- konum / renk seçici ----------------
    def start_picker(self, mode):
        self.is_picking = mode
        msg = "Fareyle git → 'X' bas" if mode == "loc" else "Fareyle git → 'C' bas"
        self.btn_pick.configure(text=msg, fg_color=SUCCESS)

    def _on_picker_key(self, key):
        if not self.is_picking:
            return
        if not isinstance(key, KeyCode) or not key.char:
            return
        ch = key.char.lower()
        if self.is_picking == "loc" and ch == "x":
            self._capture_pos(color=False)
        elif self.is_picking == "color" and ch == "c":
            self._capture_pos(color=True)

    def _capture_pos(self, color):
        if not HAS_PYAUTOGUI:
            return
        x, y = pyautogui.position()
        rgb = None
        if color:
            try:
                rgb = pyautogui.pixel(x, y)
            except Exception:
                rgb = None
        if self.use_window_mode.get():
            wid = self._target_wid()
            if wid and HAS_X11:
                try:
                    b = X11Backend()
                    ox, oy = b.abs_origin(wid)
                    b.close()
                    x -= ox; y -= oy
                except Exception:
                    pass
        self.temp_x.set(int(x)); self.temp_y.set(int(y))
        if color and rgb:
            self.picked_color.set(f"{rgb[0]},{rgb[1]},{rgb[2]}")
        self.is_picking = False
        self.root.after(0, lambda: self.btn_pick.configure(text="✅ Alındı!", fg_color=CARD2))
        self.root.after(900, self._update_editor_ui)

    # ---------------- hotkeys ----------------
    def _start_hotkeys(self):
        def on_press(key):
            if key == Key.f6:
                self.root.after(0, self.toggle_macro)
            elif key == Key.f7:
                self.root.after(0, self.toggle_clicker)
        threading.Thread(
            target=lambda: keyboard.Listener(on_press=on_press).start(),
            daemon=True).start()

    # ---------------- hızlı tıklayıcı ----------------
    def toggle_clicker(self):
        if self.is_clicker_running:
            self.is_clicker_running = False
            self.btn_clicker.configure(text="▶ Başlat", fg_color=WARN)
            self.lbl_clicker.configure(text="DURDU", text_color=MUTED)
        else:
            self.is_clicker_running = True
            self.btn_clicker.configure(text="⏹ Durdur", fg_color=DANGER)
            self.lbl_clicker.configure(text="● AKTİF", text_color=SUCCESS)
            threading.Thread(target=self._run_clicker, daemon=True).start()

    def _run_clicker(self):
        backend = None
        wid = self._target_wid()
        win_mode = self.use_window_mode.get()
        method = self.click_method.get()
        key = self.signal_key.get() or "Enter"

        if win_mode and HAS_X11:
            try:
                backend = X11Backend()
                if wid:
                    backend.focus_window(wid)
                    time.sleep(0.25)
            except Exception:
                backend = None

        last_focus_check = 0.0
        while self.is_clicker_running:
            delay = 1.0 / max(self.cps.get(), 0.1)
            try:
                # Klavye sinyali odaklı pencereye gider; oyun aktif kalmalı.
                if win_mode and backend and wid:
                    now = time.time()
                    if now - last_focus_check > 0.6 and not backend.is_active(wid):
                        backend.focus_window(wid)
                        time.sleep(0.05)
                        last_focus_check = now

                if win_mode and backend and method == "Klavye Sinyali":
                    backend.send_key(key)
                elif win_mode and backend and wid:  # İmleç Işınla
                    ox, oy = backend.abs_origin(wid)
                    tx = self.temp_x.get() or 0
                    ty = self.temp_y.get() or 0
                    backend.warp_click(ox + tx, oy + ty)
                elif HAS_PYAUTOGUI:
                    pyautogui.click()
            except Exception:
                pass
            time.sleep(delay * (random.uniform(0.9, 1.1) if self.human_speed.get() else 1.0))

        if backend:
            backend.close()

    # ---------------- makro ----------------
    def toggle_macro(self):
        if self.is_macro_running:
            self.is_macro_running = False
            self.btn_play.configure(text="▶ MAKROYU BAŞLAT  (F6)", fg_color=ACCENT)
        else:
            if not self.actions:
                return
            self.is_macro_running = True
            self.btn_play.configure(text="⏹ ÇALIŞIYOR  (F6 ile durdur)", fg_color=DANGER)
            threading.Thread(target=self._run_macro, daemon=True).start()

    def _run_macro(self):
        backend = None
        wid = self._target_wid()
        win_mode = self.use_window_mode.get()
        method = self.click_method.get()
        skey = self.signal_key.get() or "Enter"

        if win_mode and HAS_X11:
            try:
                backend = X11Backend()
                if wid:
                    backend.focus_window(wid)
                    time.sleep(0.2)
            except Exception:
                backend = None

        loops = self.loop_count.get()
        cnt = 0
        last_focus_check = 0.0
        while self.is_macro_running:
            if loops > 0 and cnt >= loops:
                break
            ox = oy = 0
            if win_mode and backend and wid:
                ox, oy = backend.abs_origin(wid)

            for act in self.actions:
                if not self.is_macro_running:
                    break
                # oyun aktif pencere kalsın (klavye sinyali odağa gider)
                if win_mode and backend and wid:
                    now = time.time()
                    if now - last_focus_check > 0.6 and not backend.is_active(wid):
                        backend.focus_window(wid)
                        time.sleep(0.05)
                        last_focus_check = now
                d = act.get("delay", 0)
                if act["type"] == "WaitColor":
                    self._wait_color(act, ox, oy)
                    continue
                elif d > 0:
                    if self.human_speed.get():
                        d *= random.uniform(0.85, 1.15)
                    time.sleep(d)

                try:
                    if act["type"] == "Click":
                        if win_mode and backend and method == "Klavye Sinyali":
                            backend.send_key(skey)
                        elif win_mode and backend and wid:
                            backend.warp_click(ox + act["x"], oy + act["y"])
                        elif HAS_PYAUTOGUI:
                            jx = random.randint(-2, 2) if self.human_speed.get() else 0
                            jy = random.randint(-2, 2) if self.human_speed.get() else 0
                            pyautogui.click(act["x"] + jx, act["y"] + jy)
                    elif act["type"] == "Press":
                        if win_mode and backend:
                            backend.send_key(act["key"])
                        elif HAS_PYAUTOGUI:
                            pyautogui.press(act["key"])
                    elif act["type"] == "Scroll" and HAS_PYAUTOGUI:
                        pyautogui.scroll(act["amount"])
                except Exception:
                    pass
            cnt += 1

        if backend:
            backend.close()
        self.is_macro_running = False
        self.root.after(0, lambda: self.btn_play.configure(
            text="▶ MAKROYU BAŞLAT  (F6)", fg_color=ACCENT))

    def _wait_color(self, act, ox, oy):
        if not HAS_PYAUTOGUI:
            return
        try:
            trgb = tuple(map(int, act["color"].split(",")))
        except Exception:
            return
        cx, cy = act["x"] + ox, act["y"] + oy
        start = time.time()
        while time.time() - start < act.get("delay", 5):
            if not self.is_macro_running:
                return
            try:
                if pyautogui.pixelMatchesColor(cx, cy, trgb, tolerance=12):
                    return
            except Exception:
                pass
            time.sleep(0.1)

    # ---------------- kayıt ----------------
    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.btn_rec.configure(text="🔴 Canlı Kayıt", fg_color=DANGER)
            if getattr(self, "mouse_listener", None):
                self.mouse_listener.stop()
        else:
            self.is_recording = True
            self.btn_rec.configure(text="⏹ Bitir (ESC)", fg_color=CARD2)
            self.actions = []
            self.refresh_tree()
            self.start_rec_time = time.time()
            try:
                from pynput import mouse
                self.mouse_listener = mouse.Listener(on_click=self._on_record_click)
                self.mouse_listener.start()
            except Exception:
                pass
            threading.Thread(target=self._esc_watcher, daemon=True).start()

    def _esc_watcher(self):
        def on_rel(key):
            if key == Key.esc:
                self.root.after(0, self.toggle_recording)
                return False
        with keyboard.Listener(on_release=on_rel) as l:
            l.join()

    def _on_record_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            delay = round(time.time() - self.start_rec_time, 2)
            self.start_rec_time = time.time()
            if self.use_window_mode.get() and HAS_X11:
                wid = self._target_wid()
                if wid:
                    try:
                        b = X11Backend(); ox, oy = b.abs_origin(wid); b.close()
                        x -= ox; y -= oy
                    except Exception:
                        pass
            self.actions.append({"type": "Click", "x": int(x), "y": int(y), "delay": delay})
            self.root.after(0, self.refresh_tree)

    # ---------------- liste işlemleri ----------------
    def add_manual_action(self):
        try:
            atype = self.manual_type.get()
            delay = float(self.ent_delay_var.get())
            act = {"type": atype, "delay": delay}
            if atype == "Click":
                act["x"] = self.temp_x.get(); act["y"] = self.temp_y.get()
            elif atype == "WaitColor":
                act["x"] = self.temp_x.get(); act["y"] = self.temp_y.get()
                act["color"] = self.picked_color.get()
            elif atype == "Press":
                act["key"] = self.input_widgets["key"].get()
            elif atype == "Scroll":
                act["amount"] = int(self.input_widgets["amount"].get())
            self.actions.append(act)
            self.refresh_tree()
        except Exception:
            messagebox.showerror("Hata", "Değerleri kontrol et.")

    def refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for i, a in enumerate(self.actions):
            det = ""
            if a["type"] == "Click":
                det = f"Pos: {a.get('x')},{a.get('y')}"
            elif a["type"] == "WaitColor":
                det = f"{a.get('color')} @ {a.get('x')},{a.get('y')}"
            elif a["type"] == "Press":
                det = f"Tuş: {a.get('key')}"
            elif a["type"] == "Scroll":
                det = f"Miktar: {a.get('amount')}"
            self.tree.insert("", "end", values=(i + 1, a["type"], det, a.get("delay")))

    def delete_row(self):
        sel = self.tree.selection()
        if sel:
            del self.actions[self.tree.index(sel[0])]
            self.refresh_tree()

    def move_row(self, d):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0]); n = idx + d
        if 0 <= n < len(self.actions):
            self.actions[idx], self.actions[n] = self.actions[n], self.actions[idx]
            self.refresh_tree()
            self.tree.selection_set(self.tree.get_children()[n])

    def save_project(self):
        f = filedialog.asksaveasfilename(defaultextension=".json")
        if f:
            with open(f, "w") as file:
                json.dump(self.actions, file)

    def load_project(self):
        f = filedialog.askopenfilename()
        if f:
            with open(f) as file:
                self.actions = json.load(file)
            self.refresh_tree()

    # ---------------- config ----------------
    def _load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json") as f:
                    d = json.load(f)
                self.cps.set(d.get("cps", d.get("f7", 15)))
                self.signal_key.set(d.get("key", "Enter"))
                self.use_window_mode.set(d.get("window_mode", True))
                self.click_method.set(d.get("method", "Klavye Sinyali"))
                self.lbl_cps.configure(text=str(int(self.cps.get())))
            except Exception:
                pass

    def _save_config(self):
        d = {"cps": self.cps.get(), "key": self.signal_key.get(),
             "window_mode": self.use_window_mode.get(),
             "method": self.click_method.get()}
        try:
            with open("config.json", "w") as f:
                json.dump(d, f)
        except Exception:
            pass

    def _toggle_top(self):
        self.root.attributes("-topmost", self.always_on_top.get())

    def on_close(self):
        self.is_clicker_running = False
        self.is_macro_running = False
        self._save_config()
        self.root.destroy()
        os._exit(0)


if __name__ == "__main__":
    root = ctk.CTk()
    app = ShadowMacroV9(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

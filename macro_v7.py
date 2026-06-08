import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import time
import threading
import random
import json
import ctypes
import os
import pygetwindow as gw
from pynput import mouse, keyboard
from pynput.keyboard import Key, KeyCode

# --- GÜVENLİK ---
pyautogui.FAILSAFE = True

# --- WINDOWS API (TURBO CLICK) ---
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class ShadowMacroV7:
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowMacro V7 - Mastermind")
        self.root.geometry("950x800")
        self.root.configure(bg="#1e1e1e")
        
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
        
        # F7 Ayarları
        self.f7_cps = tk.DoubleVar(value=10.0) # Saniyedeki tıklama
        
        # Editör Değişkenleri
        self.manual_type = tk.StringVar(value="Click")
        self.temp_x = tk.IntVar(value=0)
        self.temp_y = tk.IntVar(value=0)
        self.picked_color = tk.StringVar(value="") # Renk kodu
        
        # Listenerlar
        self.mouse_listener = None
        self.keyboard_listener = None
        
        self.setup_styles()
        self.create_gui()
        self.load_config() # Ayarları yükle
        self.start_hotkey_listener()
        
        # Global Picker Listener
        self.picker_listener = keyboard.Listener(on_release=self.on_picker_key)
        self.picker_listener.start()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        self.colors = {
            "bg": "#1e1e1e", "panel": "#252526", "fg": "#ffffff",
            "accent": "#007acc", "green": "#28a745", "red": "#d9534f", "orange": "#ff9800",
            "dark": "#181818", "input": "#3e3e42"
        }
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground="white", font=("Segoe UI", 10))
        style.configure("TButton", background="#333", foreground="white", borderwidth=0, font=("Segoe UI", 9))
        style.map("TButton", background=[("active", self.colors["accent"])])
        style.configure("Treeview", background=self.colors["panel"], foreground="white", fieldbackground=self.colors["panel"], font=("Consolas", 10), rowheight=25)
        style.configure("Treeview.Heading", background="#333", foreground="white", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", self.colors["accent"])])

    def create_gui(self):
        # ÜST PANEL (HEADER)
        header = tk.Frame(self.root, bg=self.colors["panel"], pady=10, padx=15)
        header.pack(fill="x")
        tk.Label(header, text="SHADOW MACRO V7", font=("Segoe UI", 18, "bold"), fg=self.colors["accent"], bg=self.colors["panel"]).pack(side="left")
        
        # Pencere Üstte Tutma
        ttk.Checkbutton(header, text="📌 Pencereyi Sabitle", variable=self.always_on_top, command=self.toggle_always_on_top).pack(side="right")

        # --- ORTA BÖLÜM (SOL: TABLO, SAĞ: EDİTÖR) ---
        main_body = tk.Frame(self.root, bg=self.colors["bg"], padx=10, pady=10)
        main_body.pack(fill="both", expand=True)

        # SOL: TABLO
        left_frame = tk.Frame(main_body, bg=self.colors["bg"])
        left_frame.pack(side="left", fill="both", expand=True)
        
        cols = ("ID", "Type", "Detail", "Delay")
        self.tree = ttk.Treeview(left_frame, columns=cols, show='headings', selectmode="browse")
        self.tree.heading("ID", text="#"); self.tree.column("ID", width=30, anchor="center")
        self.tree.heading("Type", text="İşlem"); self.tree.column("Type", width=80)
        self.tree.heading("Detail", text="Detay"); self.tree.column("Detail", width=250)
        self.tree.heading("Delay", text="Süre"); self.tree.column("Delay", width=60, anchor="center")
        
        scroll = tk.Scrollbar(left_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        # Tablo Butonları
        l_btns = tk.Frame(left_frame, bg=self.colors["bg"], pady=5)
        l_btns.pack(fill="x", side="bottom")
        tk.Button(l_btns, text="⬆", width=3, bg="#444", command=lambda: self.move_row(-1)).pack(side="left", padx=1)
        tk.Button(l_btns, text="⬇", width=3, bg="#444", command=lambda: self.move_row(1)).pack(side="left", padx=1)
        tk.Button(l_btns, text="❌ Sil", bg=self.colors["red"], command=self.delete_row).pack(side="right")
        tk.Button(l_btns, text="💾 Projeyi Kaydet", bg="#555", command=self.save_project).pack(side="right", padx=10)
        tk.Button(l_btns, text="📂 Proje Aç", bg="#555", command=self.load_project).pack(side="right")

        # SAĞ: GELİŞMİŞ EDİTÖR
        right_frame = tk.LabelFrame(main_body, text=" İşlem Editörü ", bg="#2d2d30", fg="#aaa", font=("Segoe UI", 10, "bold"), width=320)
        right_frame.pack(side="right", fill="y", padx=(10,0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="İşlem Tipi Seç:", bg="#2d2d30", fg="white").pack(anchor="w", padx=10, pady=(10,0))
        self.cb_type = ttk.Combobox(right_frame, textvariable=self.manual_type, values=["Click", "Press", "Scroll", "WaitColor"], state="readonly")
        self.cb_type.pack(fill="x", padx=10, pady=5)
        self.cb_type.bind("<<ComboboxSelected>>", self.update_editor_ui)

        # Dinamik Alan
        self.dynamic_frame = tk.Frame(right_frame, bg="#2d2d30")
        self.dynamic_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_pick = tk.Button(right_frame, text="🎯 Konum Seç (X)", bg=self.colors["orange"], fg="black", font=("Segoe UI", 9, "bold"), command=lambda: self.start_picker("loc"))

        tk.Label(right_frame, text="Bekleme / Timeout (sn):", bg="#2d2d30", fg="white").pack(anchor="w", padx=10, pady=(10,0))
        self.ent_delay = tk.Entry(right_frame, bg=self.colors["input"], fg="white")
        self.ent_delay.insert(0, "0.1")
        self.ent_delay.pack(fill="x", padx=10, pady=5)

        tk.Button(right_frame, text="➕ Listeye Ekle", bg=self.colors["green"], font=("Segoe UI", 10, "bold"), command=self.add_manual_action).pack(fill="x", padx=10, pady=15)
        
        # Kayıt Butonu
        tk.Frame(right_frame, height=1, bg="#444").pack(fill="x", pady=5)
        self.btn_rec = tk.Button(right_frame, text="🔴 CANLI KAYIT MODU", bg=self.colors["red"], font=("Segoe UI", 10, "bold"), command=self.toggle_recording)
        self.btn_rec.pack(fill="x", padx=10, pady=5)

        # --- ALT PANEL: F7 & F6 KONTROLLERİ ---
        bot_panel = tk.Frame(self.root, bg="#181818", pady=10, padx=10)
        bot_panel.pack(fill="x", side="bottom")

        # F7 Bölümü (YENİ)
        f7_frame = tk.LabelFrame(bot_panel, text=" F7 Auto-Clicker ", bg="#181818", fg=self.colors["orange"], font=("Segoe UI", 9, "bold"))
        f7_frame.pack(side="left", fill="y", padx=10)
        
        tk.Label(f7_frame, text="Hız (CPS):", bg="#181818").pack(side="left", padx=5)
        tk.Scale(f7_frame, from_=1, to=100, orient="horizontal", variable=self.f7_cps, bg="#181818", fg="white", length=100).pack(side="left")
        self.lbl_f7_status = tk.Label(f7_frame, text="[F7: DURDU]", fg="#555", bg="#181818", width=12)
        self.lbl_f7_status.pack(side="left", padx=10)

        # F6 Makro Bölümü
        f6_frame = tk.LabelFrame(bot_panel, text=" F6 Makro Kontrol ", bg="#181818", fg=self.colors["accent"], font=("Segoe UI", 9, "bold"))
        f6_frame.pack(side="right", fill="both", expand=True, padx=10)
        
        self.btn_play = tk.Button(f6_frame, text="▶ MAKROYU BAŞLAT (F6)", bg=self.colors["accent"], font=("Segoe UI", 11, "bold"), command=self.start_macro_thread)
        self.btn_play.pack(side="left", padx=10)
        
        tk.Label(f6_frame, text="Tekrar:", bg="#181818").pack(side="left")
        tk.Entry(f6_frame, textvariable=self.loop_count, width=5, bg="#333", fg="white").pack(side="left", padx=5)
        ttk.Checkbutton(f6_frame, text="Turbo", variable=self.use_turbo_mode).pack(side="left", padx=5)
        ttk.Checkbutton(f6_frame, text="Anti-Bot", variable=self.human_speed).pack(side="left")

        # Durum Çubuğu
        self.status_bar = tk.Label(self.root, text="Sistem Hazır", bg=self.colors["accent"], fg="white", anchor="w", padx=10)
        self.status_bar.pack(side="bottom", fill="x")
        
        self.input_widgets = {}
        self.update_editor_ui(None)

    # --- HIZLI TIKLAMA (CTYPES) ---
    def fast_click(self, x=None, y=None):
        if x is not None and y is not None:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    # --- F7 AUTO CLICKER (YENİ ÖZELLİK) ---
    def toggle_f7_clicker(self):
        if self.is_f7_running:
            self.is_f7_running = False
            self.lbl_f7_status.config(text="[F7: DURDU]", fg="#555")
        else:
            self.is_f7_running = True
            self.lbl_f7_status.config(text="[F7: ÇALIŞIYOR]", fg=self.colors["orange"])
            threading.Thread(target=self.run_f7_loop, daemon=True).start()

    def run_f7_loop(self):
        while self.is_f7_running:
            try:
                # Turbo mod açıksa Ctypes kullan, değilse pyautogui
                if self.use_turbo_mode.get():
                    self.fast_click() # Koordinat vermezsek olduğu yere tıklar
                    delay = 1.0 / self.f7_cps.get()
                    if delay > 0.001: time.sleep(delay)
                else:
                    pyautogui.click()
                    delay = 1.0 / self.f7_cps.get()
                    time.sleep(delay + random.uniform(0.01, 0.03)) # Ufak insansı sapma
            except: pass
        self.lbl_f7_status.config(text="[F7: DURDU]", fg="#555")

    # --- EDİTÖR GÜNCELLEME ---
    def update_editor_ui(self, event):
        for w in self.dynamic_frame.winfo_children(): w.destroy()
        self.btn_pick.pack_forget()
        
        atype = self.manual_type.get()
        
        if atype == "Click":
            row = tk.Frame(self.dynamic_frame, bg="#2d2d30"); row.pack(fill="x")
            tk.Label(row, text="X:", bg="#2d2d30").pack(side="left")
            self.input_widgets["x"] = tk.Entry(row, textvariable=self.temp_x, width=6, bg="#333", fg="white"); self.input_widgets["x"].pack(side="left", padx=2)
            tk.Label(row, text="Y:", bg="#2d2d30").pack(side="left")
            self.input_widgets["y"] = tk.Entry(row, textvariable=self.temp_y, width=6, bg="#333", fg="white"); self.input_widgets["y"].pack(side="left", padx=2)
            self.btn_pick.config(text="🎯 Konum Seç (X)", command=lambda: self.start_picker("loc"))
            self.btn_pick.pack(fill="x", padx=10, pady=5, in_=self.dynamic_frame.master)
            
        elif atype == "WaitColor":
            tk.Label(self.dynamic_frame, text="Renk (R,G,B):", bg="#2d2d30").pack(anchor="w")
            self.input_widgets["color"] = tk.Entry(self.dynamic_frame, textvariable=self.picked_color, bg="#333", fg="white"); self.input_widgets["color"].pack(fill="x")
            
            row = tk.Frame(self.dynamic_frame, bg="#2d2d30"); row.pack(fill="x", pady=5)
            tk.Label(row, text="X:", bg="#2d2d30").pack(side="left")
            self.input_widgets["x"] = tk.Entry(row, textvariable=self.temp_x, width=6, bg="#333", fg="white"); self.input_widgets["x"].pack(side="left")
            tk.Label(row, text="Y:", bg="#2d2d30").pack(side="left")
            self.input_widgets["y"] = tk.Entry(row, textvariable=self.temp_y, width=6, bg="#333", fg="white"); self.input_widgets["y"].pack(side="left")
            
            self.btn_pick.config(text="👁️ Renk & Konum Al (C)", command=lambda: self.start_picker("color"))
            self.btn_pick.pack(fill="x", padx=10, pady=5, in_=self.dynamic_frame.master)
            
        elif atype == "Press":
            tk.Label(self.dynamic_frame, text="Tuş:", bg="#2d2d30").pack(anchor="w")
            self.input_widgets["key"] = tk.Entry(self.dynamic_frame, bg="#333", fg="white"); self.input_widgets["key"].pack(fill="x")
            
        elif atype == "Scroll":
            tk.Label(self.dynamic_frame, text="Miktar:", bg="#2d2d30").pack(anchor="w")
            self.input_widgets["amount"] = tk.Entry(self.dynamic_frame, bg="#333", fg="white"); self.input_widgets["amount"].insert(0, "-100"); self.input_widgets["amount"].pack(fill="x")

    # --- PICKER (SEÇİCİ) ---
    def start_picker(self, mode):
        self.is_picking = mode # "loc" or "color"
        key_name = 'X' if mode == 'loc' else 'C'
        self.btn_pick.config(text=f"Mouse İle Git -> '{key_name}' Bas", bg=self.colors["green"])

    def on_picker_key(self, key):
        if not self.is_picking: return
        try:
            if self.is_picking == "loc" and isinstance(key, KeyCode) and key.char.lower() == 'x':
                x, y = pyautogui.position()
                self.temp_x.set(x); self.temp_y.set(y)
                self.stop_picker()
            elif self.is_picking == "color" and isinstance(key, KeyCode) and key.char.lower() == 'c':
                x, y = pyautogui.position()
                r, g, b = pyautogui.pixel(x, y)
                self.temp_x.set(x); self.temp_y.set(y)
                self.picked_color.set(f"{r},{g},{b}")
                self.stop_picker()
        except: pass

    def stop_picker(self):
        self.is_picking = False
        self.root.after(0, lambda: self.btn_pick.config(text="Seçim Alındı!", bg=self.colors["accent"]))
        self.root.after(1000, lambda: self.update_editor_ui(None)) # Reset button text

    # --- LİSTE & DOSYA ---
    def add_manual_action(self):
        try:
            delay = float(self.ent_delay.get())
            atype = self.manual_type.get()
            act = {"type": atype, "delay": delay}
            
            if atype == "Click":
                act["x"] = self.temp_x.get(); act["y"] = self.temp_y.get()
                detail = f"Click @ {act['x']},{act['y']}"
            elif atype == "WaitColor":
                act["x"] = self.temp_x.get(); act["y"] = self.temp_y.get()
                act["color"] = self.picked_color.get() # "255,0,0"
                detail = f"WaitColor [{act['color']}] @ {act['x']},{act['y']}"
            elif atype == "Press":
                act["key"] = self.input_widgets["key"].get(); detail = f"Press: {act['key']}"
            elif atype == "Scroll":
                act["amount"] = int(self.input_widgets["amount"].get()); detail = f"Scroll: {act['amount']}"
                
            self.actions.append(act)
            self.refresh_tree()
        except: messagebox.showerror("Hata", "Giriş değerlerini kontrol et.")

    def refresh_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for i, a in enumerate(self.actions):
            desc = ""
            if a["type"] == "Click": desc = f"Pos: {a['x']}, {a['y']}"
            elif a["type"] == "WaitColor": desc = f"Color: {a['color']} At: {a['x']}, {a['y']}"
            elif a["type"] == "Press": desc = f"Key: {a['key']}"
            self.tree.insert("", "end", values=(i+1, a["type"], desc, a["delay"]))

    def delete_row(self):
        sel = self.tree.selection()
        if sel: 
            del self.actions[self.tree.index(sel[0])]
            self.refresh_tree()
            
    def move_row(self, d):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0]); n_idx = idx + d
        if 0 <= n_idx < len(self.actions):
            self.actions[idx], self.actions[n_idx] = self.actions[n_idx], self.actions[idx]
            self.refresh_tree(); self.tree.selection_set(self.tree.get_children()[n_idx])

    def save_project(self):
        f = filedialog.asksaveasfilename(defaultextension=".json")
        if f: 
            with open(f, 'w') as file: json.dump(self.actions, file)
            
    def load_project(self):
        f = filedialog.askopenfilename()
        if f:
            with open(f, 'r') as file: self.actions = json.load(file)
            self.refresh_tree()

    # --- AYARLAR KAYIT SİSTEMİ (CONFIG) ---
    def load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    data = json.load(f)
                    self.f7_cps.set(data.get("f7_cps", 10))
                    self.use_turbo_mode.set(data.get("turbo", False))
                    self.human_speed.set(data.get("antibot", True))
                    self.always_on_top.set(data.get("top", False))
                    self.toggle_always_on_top()
            except: pass

    def save_config(self):
        data = {
            "f7_cps": self.f7_cps.get(),
            "turbo": self.use_turbo_mode.get(),
            "antibot": self.human_speed.get(),
            "top": self.always_on_top.get()
        }
        with open("config.json", "w") as f: json.dump(data, f)
    
    def toggle_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    # --- MAKRO MOTORU (F6) ---
    def start_hotkey_listener(self):
        # F6 ve F7 için listener
        def on_press(key):
            if key == Key.f6: self.toggle_macro()
            elif key == Key.f7: self.toggle_f7_clicker()
        
        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    def toggle_macro(self):
        if self.is_macro_running: 
            self.is_macro_running = False
            self.status_bar.config(text="Makro Durduruldu", bg=self.colors["red"])
        else: 
            self.start_macro_thread()

    def start_macro_thread(self):
        if not self.actions: return
        self.is_macro_running = True
        self.status_bar.config(text="Makro Çalışıyor...", bg=self.colors["green"])
        threading.Thread(target=self.run_macro, daemon=True).start()

    def run_macro(self):
        loops = self.loop_count.get()
        cnt = 0
        while self.is_macro_running:
            if loops > 0 and cnt >= loops: break
            
            for act in self.actions:
                if not self.is_macro_running: break
                
                # WaitColor Özel Mantığı
                if act["type"] == "WaitColor":
                    target_rgb = tuple(map(int, act["color"].split(','))) # "255,0,0" -> (255, 0, 0)
                    cx, cy = act["x"], act["y"]
                    timeout = act["delay"] # WaitColor'da delay = timeout
                    start_wait = time.time()
                    
                    found = False
                    while time.time() - start_wait < timeout:
                        if not self.is_macro_running: break
                        if pyautogui.pixelMatchesColor(cx, cy, target_rgb, tolerance=10):
                            found = True
                            break
                        time.sleep(0.1)
                    
                    if not found: 
                        print("Renk bulunamadı, geçiliyor...")
                        continue # Renk bulunamadıysa tıklamadan sonraki adıma geç
                
                # Normal Bekleme
                elif act["type"] != "WaitColor":
                    d = act["delay"]
                    if self.human_speed.get() and not self.use_turbo_mode.get(): d *= random.uniform(0.8, 1.2)
                    if d > 0: time.sleep(d)

                # Aksiyonlar
                try:
                    if act["type"] == "Click":
                        if self.use_turbo_mode.get():
                            self.fast_click(act["x"], act["y"])
                        else:
                            pyautogui.click(act["x"], act["y"])
                    elif act["type"] == "Press":
                        pyautogui.press(act["key"])
                    elif act["type"] == "Scroll":
                        pyautogui.scroll(act["amount"])
                except: pass
            
            cnt += 1
        self.is_macro_running = False
        self.status_bar.config(text="Makro Bitti", bg="#007acc")

    # --- KAYIT MODU ---
    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.btn_rec.config(text="🔴 CANLI KAYIT MODU", bg=self.colors["red"])
            if self.mouse_listener: self.mouse_listener.stop()
        else:
            self.is_recording = True
            self.btn_rec.config(text="⏹ KAYDI BİTİR (ESC)", bg="#333")
            self.actions = []
            self.refresh_tree()
            self.mouse_listener = mouse.Listener(on_click=self.on_click)
            self.mouse_listener.start()
            self.start_rec_time = time.time()
            
            # ESC Listener
            def stop_on_esc(key):
                if key == Key.esc: 
                    self.toggle_recording()
                    return False
            self.esc_listener = keyboard.Listener(on_release=stop_on_esc)
            self.esc_listener.start()

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            delay = round(time.time() - self.start_rec_time, 2)
            self.start_rec_time = time.time()
            self.actions.append({"type": "Click", "x": x, "y": y, "delay": delay})
            self.root.after(0, self.refresh_tree)

    def on_close(self):
        self.save_config()
        self.root.destroy()
        os._exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = ShadowMacroV7(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
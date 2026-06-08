import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import time
import threading
import random
import json
from pynput import mouse, keyboard
from pynput.keyboard import Key

# --- GÜVENLİK ---
pyautogui.FAILSAFE = True

class ShadowMacroV3:
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowMacro V3 - Ultimate Edition")
        self.root.geometry("800x650")
        self.root.configure(bg="#1e1e1e")
        
        # Değişkenler
        self.is_running = False
        self.is_recording = False
        self.actions = [] 
        self.loop_count = tk.IntVar(value=0)
        self.human_speed = tk.BooleanVar(value=True)
        self.manual_action_type = tk.StringVar(value="Click")
        self.start_time = 0
        
        # Dinleyiciler
        self.mouse_listener = None
        self.keyboard_listener = None
        
        self.setup_styles()
        self.create_gui()
        self.start_hotkey_listener()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Renk Paleti
        self.colors = {
            "bg": "#1e1e1e", "fg": "#ffffff", "panel": "#252526",
            "accent": "#007acc", "success": "#28a745", "danger": "#d9534f",
            "warning": "#ffc107", "input": "#3e3e42"
        }
        
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 10))
        style.configure("TButton", background="#333", foreground="white", borderwidth=0, font=("Segoe UI", 9))
        style.map("TButton", background=[("active", self.colors["accent"])])
        
        # Tab Stili
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background="#333", foreground="white", padding=[10, 5], font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", self.colors["accent"])])

    def create_gui(self):
        # --- ANA TAB YAPISI ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_dashboard = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.tab_editor = tk.Frame(self.notebook, bg=self.colors["bg"])
        
        self.notebook.add(self.tab_dashboard, text="📊 Kontrol Paneli")
        self.notebook.add(self.tab_editor, text="✏️ Editör & Kayıt")

        self.setup_dashboard_tab()
        self.setup_editor_tab()
        
        # Durum Çubuğu
        self.status_bar = tk.Label(self.root, text="Sistem Hazır - Başlatmak için F6", bg="#007acc", fg="white", anchor="w", padx=10, font=("Segoe UI", 9, "bold"))
        self.status_bar.pack(side="bottom", fill="x")

    # ==========================
    # 1. TAB: DASHBOARD (OYNATMA)
    # ==========================
    def setup_dashboard_tab(self):
        frame = tk.Frame(self.tab_dashboard, bg=self.colors["bg"], padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        # Başlık
        tk.Label(frame, text="SHADOW MACRO V3", font=("Segoe UI", 24, "bold"), fg=self.colors["accent"], bg=self.colors["bg"]).pack(pady=(0, 20))
        
        # Büyük Butonlar
        btn_frame = tk.Frame(frame, bg=self.colors["bg"])
        btn_frame.pack(pady=10)
        
        self.btn_play = tk.Button(btn_frame, text="▶ BAŞLAT (F6)", bg=self.colors["success"], fg="white", font=("Segoe UI", 14, "bold"), width=20, height=2, relief="flat", command=self.start_macro_thread)
        self.btn_play.pack(pady=5)
        
        tk.Button(btn_frame, text="⏹ DURDUR (F6)", bg=self.colors["danger"], fg="white", font=("Segoe UI", 12), width=20, relief="flat", command=self.stop_macro).pack(pady=5)

        # Ayarlar Özeti
        opts_frame = tk.LabelFrame(frame, text="Hızlı Ayarlar", bg=self.colors["bg"], fg="white", font=("Segoe UI", 10, "bold"), padx=10, pady=10)
        opts_frame.pack(fill="x", pady=20)
        
        tk.Label(opts_frame, text="Tekrar Sayısı (0=Sınırsız):").pack(side="left")
        tk.Entry(opts_frame, textvariable=self.loop_count, width=5, bg=self.colors["input"], fg="white", font=("Consolas", 11)).pack(side="left", padx=10)
        
        ttk.Checkbutton(opts_frame, text="Anti-Bot (İnsan Hızı)", variable=self.human_speed).pack(side="right")

        # Dosya İşlemleri
        file_frame = tk.Frame(frame, bg=self.colors["bg"])
        file_frame.pack(fill="x", pady=10)
        
        tk.Button(file_frame, text="📂 Proje Aç (JSON)", bg="#555", fg="white", width=20, command=self.load_from_json).pack(side="left", padx=5)
        tk.Button(file_frame, text="💾 Projeyi Kaydet", bg="#555", fg="white", width=20, command=self.save_to_json).pack(side="right", padx=5)

    # ==========================
    # 2. TAB: EDİTÖR (KAYIT & DÜZENLEME)
    # ==========================
    def setup_editor_tab(self):
        main_editor = tk.Frame(self.tab_editor, bg=self.colors["bg"])
        main_editor.pack(fill="both", expand=True, padx=10, pady=10)

        # --- SOL: LİSTE ---
        left_col = tk.Frame(main_editor, bg=self.colors["bg"])
        left_col.pack(side="left", fill="both", expand=True)
        
        tk.Label(left_col, text="Aksiyon Listesi", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        
        list_scroll = tk.Scrollbar(left_col)
        list_scroll.pack(side="right", fill="y")
        
        self.action_listbox = tk.Listbox(left_col, bg=self.colors["panel"], fg="#ddd", 
                                         selectbackground=self.colors["accent"], borderwidth=0, 
                                         font=("Consolas", 10), yscrollcommand=list_scroll.set)
        self.action_listbox.pack(fill="both", expand=True, pady=5)
        list_scroll.config(command=self.action_listbox.yview)

        # Liste Kontrolleri (Yukarı/Aşağı/Sil)
        list_ctrl = tk.Frame(left_col, bg=self.colors["bg"])
        list_ctrl.pack(fill="x")
        
        tk.Button(list_ctrl, text="⬆", width=3, bg="#444", fg="white", command=lambda: self.move_item(-1)).pack(side="left", padx=1)
        tk.Button(list_ctrl, text="⬇", width=3, bg="#444", fg="white", command=lambda: self.move_item(1)).pack(side="left", padx=1)
        tk.Button(list_ctrl, text="🗑 Sil", bg=self.colors["danger"], fg="white", command=self.delete_item).pack(side="right")
        tk.Button(list_ctrl, text="🧹 Temizle", bg="#f0ad4e", fg="white", command=self.clear_all).pack(side="right", padx=5)

        # --- SAĞ: MANUEL GİRİŞ & KAYIT ---
        right_col = tk.Frame(main_editor, bg="#2d2d30", width=280, padx=10, pady=10)
        right_col.pack(side="right", fill="y", padx=(10,0))
        right_col.pack_propagate(False)

        # Kayıt Butonu (DÜZELTİLEN KISIM BURASI)
        self.btn_rec = tk.Button(right_col, text="🔴 CANLI KAYIT BAŞLAT", bg=self.colors["danger"], fg="white", font=("Segoe UI", 10, "bold"), pady=5, command=self.toggle_recording)
        # marginBottom yerine pady=(top, bottom) kullandık
        self.btn_rec.pack(fill="x", pady=(0, 15)) 
        
        tk.Label(right_col, text="--- VEYA MANUEL EKLE ---", bg="#2d2d30", fg="#777").pack(pady=10)

        # Tip Seçimi
        tk.Label(right_col, text="İşlem Tipi:", bg="#2d2d30").pack(anchor="w")
        self.combo_type = ttk.Combobox(right_col, textvariable=self.manual_action_type, values=["Click", "Press", "Scroll", "Drag"], state="readonly")
        self.combo_type.pack(fill="x")
        self.combo_type.bind("<<ComboboxSelected>>", self.update_inputs)

        # Dinamik Alanlar
        self.input_frame = tk.Frame(right_col, bg="#2d2d30")
        self.input_frame.pack(fill="x", pady=10)
        
        # Ortak Alan: Bekleme Süresi
        tk.Label(right_col, text="Bekleme (sn):", bg="#2d2d30").pack(anchor="w")
        self.ent_delay = tk.Entry(right_col, bg=self.colors["input"], fg="white")
        self.ent_delay.insert(0, "0.5")
        self.ent_delay.pack(fill="x", pady=(0, 10))

        tk.Button(right_col, text="➕ Listeye Ekle", bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), command=self.add_manual).pack(fill="x", side="bottom")

        # Input Elemanları (Referanslar)
        self.ent_x = None
        self.ent_y = None
        self.ent_key = None
        self.ent_btn = None
        self.btn_get_pos = None
        
        self.update_inputs(None) # İlk yükleme

    # --- DİNAMİK INPUT YÖNETİMİ ---
    def update_inputs(self, event):
        # Önce temizle
        for widget in self.input_frame.winfo_children():
            widget.destroy()
            
        atype = self.manual_action_type.get()
        
        if atype in ["Click", "Drag"]:
            tk.Label(self.input_frame, text="X Kordinat:", bg="#2d2d30").grid(row=0, column=0)
            self.ent_x = tk.Entry(self.input_frame, width=8, bg=self.colors["input"], fg="white")
            self.ent_x.grid(row=0, column=1, padx=5)
            
            tk.Label(self.input_frame, text="Y Kordinat:", bg="#2d2d30").grid(row=0, column=2)
            self.ent_y = tk.Entry(self.input_frame, width=8, bg=self.colors["input"], fg="white")
            self.ent_y.grid(row=0, column=3, padx=5)
            
            self.btn_get_pos = tk.Button(self.input_frame, text="📍 Konum Al (3sn)", bg="#555", fg="white", command=self.get_mouse_pos_delay)
            self.btn_get_pos.grid(row=1, column=0, columnspan=4, sticky="we", pady=5)
            
            if atype == "Click":
                tk.Label(self.input_frame, text="Buton (left/right):", bg="#2d2d30").grid(row=2, column=0, columnspan=2, sticky="w")
                self.ent_btn = tk.Entry(self.input_frame, bg=self.colors["input"], fg="white")
                self.ent_btn.insert(0, "left")
                self.ent_btn.grid(row=2, column=2, columnspan=2, sticky="we")

        elif atype == "Press":
            tk.Label(self.input_frame, text="Tuş (a, enter, f1):", bg="#2d2d30").pack(anchor="w")
            self.ent_key = tk.Entry(self.input_frame, bg=self.colors["input"], fg="white")
            self.ent_key.pack(fill="x")
            
        elif atype == "Scroll":
            tk.Label(self.input_frame, text="Miktar (+ Yukarı / - Aşağı):", bg="#2d2d30").pack(anchor="w")
            self.ent_key = tk.Entry(self.input_frame, bg=self.colors["input"], fg="white") # Miktarı key değişkeninde tutalım
            self.ent_key.insert(0, "-100")
            self.ent_key.pack(fill="x")

    def get_mouse_pos_delay(self):
        def task():
            self.btn_get_pos.config(bg="orange", text="3")
            time.sleep(1)
            self.btn_get_pos.config(text="2")
            time.sleep(1)
            self.btn_get_pos.config(text="1")
            time.sleep(1)
            x, y = pyautogui.position()
            self.root.after(0, lambda: self.fill_coords(x,y))
        threading.Thread(target=task, daemon=True).start()
        
    def fill_coords(self, x, y):
        self.ent_x.delete(0, tk.END); self.ent_x.insert(0, str(x))
        self.ent_y.delete(0, tk.END); self.ent_y.insert(0, str(y))
        self.btn_get_pos.config(bg="#555", text="Alındı")

    # --- LİSTE İŞLEMLERİ ---
    def add_manual(self):
        try:
            delay = float(self.ent_delay.get())
            atype = self.manual_action_type.get()
            action = {"type": atype.lower(), "delay": delay}
            
            if atype in ["Click", "Drag"]:
                action["x"] = int(self.ent_x.get())
                action["y"] = int(self.ent_y.get())
                if atype == "Click": action["button"] = self.ent_btn.get()
                
            elif atype == "Press":
                action["key"] = self.ent_key.get()
            elif atype == "Scroll":
                action["amount"] = int(self.ent_key.get())
                
            self.actions.append(action)
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Hata", f"Girdi Hatası: {str(e)}")

    def refresh_list(self):
        self.action_listbox.delete(0, tk.END)
        for i, act in enumerate(self.actions):
            desc = f"[{i+1}] {act['type'].upper()} "
            if "x" in act: desc += f"@ {act['x']},{act['y']} "
            if "key" in act: desc += f"Key: {act['key']} "
            if "amount" in act: desc += f"Miktar: {act['amount']} "
            desc += f"({act['delay']}s)"
            self.action_listbox.insert(tk.END, desc)
            
    def move_item(self, direction):
        sel = self.action_listbox.curselection()
        if not sel: return
        idx = sel[0]
        new_idx = idx + direction
        if 0 <= new_idx < len(self.actions):
            self.actions[idx], self.actions[new_idx] = self.actions[new_idx], self.actions[idx]
            self.refresh_list()
            self.action_listbox.select_set(new_idx)

    def delete_item(self):
        sel = self.action_listbox.curselection()
        if sel:
            del self.actions[sel[0]]
            self.refresh_list()
            
    def clear_all(self):
        self.actions = []
        self.refresh_list()

    # --- DOSYA SİSTEMİ (JSON) ---
    def save_to_json(self):
        if not self.actions: return
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("ShadowMacro Files", "*.json")])
        if f:
            with open(f, 'w') as file:
                json.dump(self.actions, file, indent=4)
            messagebox.showinfo("Başarılı", "Makro kaydedildi.")

    def load_from_json(self):
        f = filedialog.askopenfilename(filetypes=[("ShadowMacro Files", "*.json")])
        if f:
            try:
                with open(f, 'r') as file:
                    self.actions = json.load(file)
                self.refresh_list()
                self.notebook.select(self.tab_editor) # Editöre geç
            except:
                messagebox.showerror("Hata", "Dosya formatı bozuk.")

    # --- KAYIT SİSTEMİ (RECORD) ---
    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.btn_rec.config(text="🔴 CANLI KAYIT BAŞLAT", bg=self.colors["danger"])
            if self.mouse_listener: self.mouse_listener.stop()
            if self.keyboard_listener: self.keyboard_listener.stop()
            self.status_bar.config(text="Kayıt Tamamlandı.")
        else:
            self.is_recording = True
            self.actions = []
            self.refresh_list()
            self.btn_rec.config(text="⏹ KAYDI BİTİR (ESC)", bg="#333")
            self.status_bar.config(text="🔴 KAYDEDİLİYOR... ESC ile durdur.")
            self.start_time = time.time()
            
            self.mouse_listener = mouse.Listener(on_click=self.on_click, on_scroll=self.on_scroll)
            self.keyboard_listener = keyboard.Listener(on_release=self.on_key)
            self.mouse_listener.start()
            self.keyboard_listener.start()

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            delay = round(time.time() - self.start_time, 2)
            self.start_time = time.time()
            self.actions.append({"type": "click", "x": x, "y": y, "button": str(button).replace("Button.", ""), "delay": delay})
            self.root.after(0, self.refresh_list)

    def on_scroll(self, x, y, dx, dy):
        if self.is_recording:
            delay = round(time.time() - self.start_time, 2)
            self.start_time = time.time()
            amount = dy * 100 # Scroll hassasiyeti
            self.actions.append({"type": "scroll", "amount": amount, "delay": delay})
            self.root.after(0, self.refresh_list)

    def on_key(self, key):
        if key == Key.esc:
            self.toggle_recording()
            return False
        if self.is_recording and key != Key.f6:
            delay = round(time.time() - self.start_time, 2)
            self.start_time = time.time()
            try: k = key.char
            except: k = str(key).replace("Key.", "")
            self.actions.append({"type": "press", "key": k, "delay": delay})
            self.root.after(0, self.refresh_list)

    # --- OYNATMA SİSTEMİ ---
    def start_hotkey_listener(self):
        def listen():
            with keyboard.GlobalHotKeys({'<f6>': self.toggle_run}) as h: h.join()
        threading.Thread(target=listen, daemon=True).start()

    def toggle_run(self):
        if self.is_running: self.stop_macro()
        else: self.start_macro_thread()

    def stop_macro(self):
        self.is_running = False
        self.status_bar.config(text="🛑 İşlem Kullanıcı Tarafından Durduruldu.", bg=self.colors["danger"])

    def start_macro_thread(self):
        if not self.actions: 
            messagebox.showwarning("Uyarı", "Liste boş!")
            return
        if not self.is_running:
            self.is_running = True
            self.status_bar.config(text="▶ MAKRO ÇALIŞIYOR... (Durdurmak için F6)", bg=self.colors["success"])
            threading.Thread(target=self.run_logic).start()

    def run_logic(self):
        loops = self.loop_count.get()
        counter = 0
        
        while self.is_running:
            if loops > 0 and counter >= loops: break
            
            for act in self.actions:
                if not self.is_running: break
                
                # Gecikme & Anti-Bot
                delay = act["delay"]
                if self.human_speed.get():
                    delay *= random.uniform(0.8, 1.25)
                    if delay < 0.05: delay = 0.05
                time.sleep(delay)
                
                try:
                    if act["type"] == "click":
                        x, y = act["x"], act["y"]
                        if self.human_speed.get():
                            x += random.randint(-2, 2)
                            y += random.randint(-2, 2)
                        pyautogui.click(x, y, button=act.get("button", "left"))
                        
                    elif act["type"] == "press":
                        pyautogui.press(act["key"])
                        
                    elif act["type"] == "scroll":
                        pyautogui.scroll(act["amount"])
                        
                    elif act["type"] == "drag":
                        # Drag işlemi: O anki konumdan belirtilen konuma sürükle
                        pyautogui.dragTo(act["x"], act["y"], duration=random.uniform(0.3, 0.6))
                        
                except Exception as e:
                    print(f"Hata: {e}")
            
            counter += 1
            
        self.is_running = False
        self.status_bar.config(text="✅ Makro Tamamlandı.", bg="#007acc")

if __name__ == "__main__":
    root = tk.Tk()
    app = ShadowMacroV3(root)
    root.mainloop()
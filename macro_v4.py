import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import time
import threading
import random
import json
import pygetwindow as gw # Pencere yakalama kütüphanesi
from pynput import mouse, keyboard
from pynput.keyboard import Key

# --- AYARLAR ---
pyautogui.FAILSAFE = True

class ShadowMacroV4:
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowMacro V4 - Window Hunter")
        self.root.geometry("850x700")
        self.root.configure(bg="#1e1e1e")
        
        # Değişkenler
        self.is_running = False
        self.is_recording = False
        self.actions = [] 
        self.loop_count = tk.IntVar(value=0)
        self.human_speed = tk.BooleanVar(value=True)
        self.use_relative_coords = tk.BooleanVar(value=False) # Pencere modu aktif mi?
        self.target_window_title = tk.StringVar()
        self.manual_action_type = tk.StringVar(value="Click")
        self.start_time = 0
        
        # Listenerlar
        self.mouse_listener = None
        self.keyboard_listener = None
        
        self.setup_styles()
        self.create_gui()
        self.start_hotkey_listener()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        self.colors = {
            "bg": "#1e1e1e", "fg": "#ffffff", "panel": "#252526",
            "accent": "#007acc", "success": "#28a745", "danger": "#d9534f",
            "warning": "#ffc107", "input": "#3e3e42"
        }
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 10))
        style.configure("TButton", background="#333", foreground="white", borderwidth=0, font=("Segoe UI", 9))
        style.map("TButton", background=[("active", self.colors["accent"])])
        style.configure("TCheckbutton", background=self.colors["bg"], foreground="white", font=("Segoe UI", 10))

    def create_gui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_dash = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.tab_edit = tk.Frame(self.notebook, bg=self.colors["bg"])
        
        self.notebook.add(self.tab_dash, text="🎮 Kontrol & Pencere")
        self.notebook.add(self.tab_edit, text="✏️ Editör")

        self.setup_dashboard()
        self.setup_editor()
        
        self.status_bar = tk.Label(self.root, text="Sistem Hazır - F6 Başlat/Durdur", bg="#007acc", fg="white", anchor="w", padx=10, font=("Segoe UI", 9, "bold"))
        self.status_bar.pack(side="bottom", fill="x")

    def setup_dashboard(self):
        frame = tk.Frame(self.tab_dash, bg=self.colors["bg"], padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        # --- PENCERE SEÇİM ALANI (YENİ) ---
        win_frame = tk.LabelFrame(frame, text=" Hedef Pencere Ayarları ", bg=self.colors["bg"], fg="#00afff", font=("Segoe UI", 11, "bold"), padx=15, pady=15)
        win_frame.pack(fill="x", pady=(0, 20))
        
        row1 = tk.Frame(win_frame, bg=self.colors["bg"])
        row1.pack(fill="x")
        
        tk.Label(row1, text="Hedef Pencere:").pack(side="left")
        self.combo_windows = ttk.Combobox(row1, textvariable=self.target_window_title, width=40, state="readonly")
        self.combo_windows.pack(side="left", padx=10)
        tk.Button(row1, text="🔄 Yenile", bg="#444", fg="white", command=self.refresh_windows).pack(side="left")
        
        row2 = tk.Frame(win_frame, bg=self.colors["bg"])
        row2.pack(fill="x", pady=(10, 0))
        
        ttk.Checkbutton(row2, text="Pencereye Kitle (Pencere Modu)", variable=self.use_relative_coords, command=self.toggle_mode_info).pack(side="left")
        self.lbl_mode_info = tk.Label(row2, text="(Seçili pencereye göre işlem yapar, pencere hareket etse de çalışır)", fg="#aaa", font=("Segoe UI", 8))
        self.lbl_mode_info.pack(side="left", padx=10)

        # --- KONTROLLER ---
        ctrl_frame = tk.Frame(frame, bg=self.colors["bg"])
        ctrl_frame.pack(fill="both", expand=True)

        self.btn_play = tk.Button(ctrl_frame, text="▶ BAŞLAT (F6)", bg=self.colors["success"], fg="white", font=("Segoe UI", 14, "bold"), height=2, command=self.start_macro_thread)
        self.btn_play.pack(fill="x", pady=5)
        
        tk.Button(ctrl_frame, text="⏹ DURDUR (F6)", bg=self.colors["danger"], fg="white", font=("Segoe UI", 12), command=self.stop_macro).pack(fill="x", pady=5)
        
        # Alt Ayarlar
        sub_opts = tk.Frame(ctrl_frame, bg=self.colors["bg"])
        sub_opts.pack(fill="x", pady=20)
        
        tk.Label(sub_opts, text="Tekrar Sayısı:").pack(side="left")
        tk.Entry(sub_opts, textvariable=self.loop_count, width=5, bg=self.colors["input"], fg="white").pack(side="left", padx=5)
        ttk.Checkbutton(sub_opts, text="Anti-Bot (İnsan Hızı)", variable=self.human_speed).pack(side="right")

        # JSON Kayıt
        io_frame = tk.Frame(ctrl_frame, bg=self.colors["bg"])
        io_frame.pack(fill="x", pady=10)
        tk.Button(io_frame, text="💾 Kaydet", bg="#555", fg="white", width=15, command=self.save_json).pack(side="left")
        tk.Button(io_frame, text="📂 Yükle", bg="#555", fg="white", width=15, command=self.load_json).pack(side="right")
        
        self.refresh_windows() # Başlangıçta pencereleri yükle

    def setup_editor(self):
        # Sol taraf liste, Sağ taraf editör (V3.1 ile aynı mantık)
        main_editor = tk.Frame(self.tab_edit, bg=self.colors["bg"])
        main_editor.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Sol
        left_col = tk.Frame(main_editor, bg=self.colors["bg"])
        left_col.pack(side="left", fill="both", expand=True)
        
        scr = tk.Scrollbar(left_col)
        scr.pack(side="right", fill="y")
        self.lst_actions = tk.Listbox(left_col, bg=self.colors["panel"], fg="#ddd", height=20, borderwidth=0, font=("Consolas", 10), yscrollcommand=scr.set)
        self.lst_actions.pack(fill="both", expand=True)
        scr.config(command=self.lst_actions.yview)
        
        btns = tk.Frame(left_col, bg=self.colors["bg"])
        btns.pack(fill="x", pady=5)
        tk.Button(btns, text="Sil", bg=self.colors["danger"], fg="white", command=self.delete_item).pack(side="right")
        tk.Button(btns, text="Temizle", bg="orange", fg="white", command=lambda: [self.actions.clear(), self.refresh_list()]).pack(side="right", padx=5)

        # Sağ
        right_col = tk.Frame(main_editor, bg="#2d2d30", width=250, padx=10, pady=10)
        right_col.pack(side="right", fill="y", padx=(10,0))
        right_col.pack_propagate(False)
        
        self.btn_rec = tk.Button(right_col, text="🔴 KAYIT (REC)", bg=self.colors["danger"], fg="white", font=("Segoe UI", 10, "bold"), command=self.toggle_recording)
        self.btn_rec.pack(fill="x", pady=(0,15))
        
        tk.Label(right_col, text="Manuel Ekle:", bg="#2d2d30", fg="#aaa").pack(anchor="w")
        self.cb_type = ttk.Combobox(right_col, textvariable=self.manual_action_type, values=["Click", "Press"], state="readonly")
        self.cb_type.pack(fill="x")
        
        self.ent_val1 = tk.Entry(right_col, bg=self.colors["input"], fg="white"); self.ent_val1.pack(fill="x", pady=5)
        self.ent_val2 = tk.Entry(right_col, bg=self.colors["input"], fg="white"); self.ent_val2.pack(fill="x", pady=5)
        
        tk.Button(right_col, text="➕ Ekle", bg=self.colors["success"], fg="white", command=self.add_manual).pack(fill="x", pady=10)
        
        # Placeholder text
        self.ent_val1.insert(0, "X Koord / Key")
        self.ent_val2.insert(0, "Y Koord / Süre")

    # --- PENCERE YÖNETİMİ ---
    def refresh_windows(self):
        try:
            # Boş başlıkları filtrele
            wins = [w.title for w in gw.getAllWindows() if w.title.strip()]
            self.combo_windows['values'] = sorted(wins)
            if wins: self.combo_windows.current(0)
        except Exception as e:
            print(f"Pencere hatası: {e}")

    def toggle_mode_info(self):
        if self.use_relative_coords.get():
            self.lbl_mode_info.config(text="✅ AKTİF: Kayıtlar pencerenin sol üst köşesine göre yapılacak.", fg="#00afff")
        else:
            self.lbl_mode_info.config(text="❌ PASİF: Kayıtlar tüm ekrana (Absolute) göre yapılacak.", fg="#aaa")

    def get_target_window_rect(self):
        title = self.target_window_title.get()
        if not title: return None
        try:
            win = gw.getWindowsWithTitle(title)[0]
            return win
        except IndexError:
            return None

    # --- KAYIT MANTIĞI ---
    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.btn_rec.config(text="🔴 KAYIT (REC)", bg=self.colors["danger"])
            if self.mouse_listener: self.mouse_listener.stop()
            if self.keyboard_listener: self.keyboard_listener.stop()
            self.status_bar.config(text="Kayıt Bitti.")
        else:
            # Pencere modu kontrolü
            if self.use_relative_coords.get():
                win = self.get_target_window_rect()
                if not win:
                    messagebox.showerror("Hata", "Pencere modunu seçtin ama bir pencere seçmedin!")
                    return
                # Pencereyi öne getir
                try: win.activate()
                except: pass
                time.sleep(0.5)

            self.is_recording = True
            self.actions = []
            self.refresh_list()
            self.btn_rec.config(text="⏹ BİTİR (ESC)", bg="#333")
            self.status_bar.config(text="🔴 KAYDEDİLİYOR...")
            self.start_time = time.time()
            
            self.mouse_listener = mouse.Listener(on_click=self.on_click)
            self.keyboard_listener = keyboard.Listener(on_release=self.on_key)
            self.mouse_listener.start()
            self.keyboard_listener.start()

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            delay = round(time.time() - self.start_time, 2)
            self.start_time = time.time()
            
            final_x, final_y = x, y
            
            # PENCERE MODU VARSA: Göreceli Koordinat Hesapla
            if self.use_relative_coords.get():
                win = self.get_target_window_rect()
                if win:
                    # Tıklanan nokta pencere içinde mi?
                    if (win.left <= x <= win.left + win.width) and (win.top <= y <= win.top + win.height):
                        final_x = x - win.left
                        final_y = y - win.top
                    else:
                        # Pencere dışına tıklandıysa kaydetme veya uyar
                        print("Pencere dışı tıklama yoksayıldı.")
                        return

            act = {"type": "click", "x": final_x, "y": final_y, "btn": str(button).replace("Button.",""), "delay": delay}
            self.actions.append(act)
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

    # --- OYNATMA MANTIĞI ---
    def start_hotkey_listener(self):
        def listen():
            with keyboard.GlobalHotKeys({'<f6>': self.toggle_run}) as h: h.join()
        threading.Thread(target=listen, daemon=True).start()

    def toggle_run(self):
        if self.is_running: self.stop_macro()
        else: self.start_macro_thread()

    def stop_macro(self):
        self.is_running = False
        self.status_bar.config(text="🛑 Durduruldu.", bg=self.colors["danger"])

    def start_macro_thread(self):
        if not self.actions: return
        if not self.is_running:
            self.is_running = True
            
            # Eğer Pencere Modu aktifse, başlatırken pencereyi bul ve öne getir
            if self.use_relative_coords.get():
                win = self.get_target_window_rect()
                if not win:
                    messagebox.showerror("Hata", "Hedef pencere bulunamadı!")
                    self.is_running = False
                    return
                try: 
                    win.activate()
                    if win.isMinimized: win.restore()
                except: pass
                time.sleep(0.5) # Pencerenin gelmesini bekle
            
            self.status_bar.config(text="▶ ÇALIŞIYOR...", bg=self.colors["success"])
            threading.Thread(target=self.run_logic).start()

    def run_logic(self):
        loops = self.loop_count.get()
        cnt = 0
        while self.is_running:
            if loops > 0 and cnt >= loops: break
            
            # Her döngü başında pencere konumunu güncelle (Pencere hareket etmiş olabilir)
            win_offset_x, win_offset_y = 0, 0
            if self.use_relative_coords.get():
                win = self.get_target_window_rect()
                if win:
                    win_offset_x = win.left
                    win_offset_y = win.top
            
            for act in self.actions:
                if not self.is_running: break
                
                # Delay
                d = act["delay"]
                if self.human_speed.get(): d *= random.uniform(0.8, 1.25)
                time.sleep(max(0.05, d))
                
                try:
                    if act["type"] == "click":
                        # Koordinat Hesapla
                        target_x = act["x"] + win_offset_x
                        target_y = act["y"] + win_offset_y
                        
                        # Anti-Bot Titreme
                        if self.human_speed.get():
                            target_x += random.randint(-2, 2)
                            target_y += random.randint(-2, 2)
                            
                        pyautogui.click(target_x, target_y, button=act.get("btn", "left"))
                        
                    elif act["type"] == "press":
                        pyautogui.press(act["key"])
                        
                except Exception as e:
                    print(f"Hata: {e}")
            cnt += 1
        self.is_running = False
        self.status_bar.config(text="Tamamlandı.", bg="#007acc")

    # --- YARDIMCILAR ---
    def refresh_list(self):
        self.lst_actions.delete(0, tk.END)
        for i, a in enumerate(self.actions):
            txt = f"[{i+1}] {a['type'].upper()} "
            if "x" in a: txt += f"@{a['x']},{a['y']} "
            if "key" in a: txt += f"[{a['key']}] "
            txt += f"({a['delay']}s)"
            self.lst_actions.insert(tk.END, txt)

    def delete_item(self):
        sel = self.lst_actions.curselection()
        if sel:
            del self.actions[sel[0]]
            self.refresh_list()

    def add_manual(self):
        try:
            t = self.manual_action_type.get()
            if t == "Click":
                x = int(self.ent_val1.get())
                y = int(self.ent_val2.get())
                self.actions.append({"type": "click", "x":x, "y":y, "delay":1.0, "btn":"left"})
            else:
                k = self.ent_val1.get()
                d = float(self.ent_val2.get())
                self.actions.append({"type": "press", "key":k, "delay":d})
            self.refresh_list()
        except: pass

    def save_json(self):
        f = filedialog.asksaveasfilename(defaultextension=".json")
        if f: 
            with open(f, 'w') as file: json.dump(self.actions, file)

    def load_json(self):
        f = filedialog.askopenfilename()
        if f:
            with open(f, 'r') as file: self.actions = json.load(file)
            self.refresh_list()

if __name__ == "__main__":
    root = tk.Tk()
    app = ShadowMacroV4(root)
    root.mainloop()
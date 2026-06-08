import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import time
import threading
import random
import json
import ctypes # Windows API erişimi için
import pygetwindow as gw
from pynput import mouse, keyboard
from pynput.keyboard import Key, KeyCode

# --- GÜVENLİK ---
pyautogui.FAILSAFE = True

# --- WINDOWS API SABİTLERİ (HIZ İÇİN) ---
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

class ShadowMacroV6:
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowMacro V6 - Speed Demon")
        self.root.geometry("900x750")
        self.root.configure(bg="#1e1e1e")
        
        # Değişkenler
        self.is_running = False
        self.is_recording = False
        self.is_picking = False 
        self.actions = [] 
        self.loop_count = tk.IntVar(value=0)
        self.human_speed = tk.BooleanVar(value=True)
        self.use_window_mode = tk.BooleanVar(value=False)
        self.use_turbo_mode = tk.BooleanVar(value=False) # YENİ: Hız Modu
        self.target_window = tk.StringVar()
        self.manual_type = tk.StringVar(value="Click")
        
        self.temp_x = tk.IntVar(value=0)
        self.temp_y = tk.IntVar(value=0)
        
        # Listenerlar
        self.mouse_listener = None
        self.keyboard_listener = None
        
        self.setup_styles()
        self.create_gui()
        self.start_hotkey_listener()
        
        self.picker_listener = keyboard.Listener(on_release=self.on_picker_key)
        self.picker_listener.start()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        self.colors = {
            "bg": "#1e1e1e", "panel": "#252526", "fg": "#ffffff",
            "accent": "#007acc", "green": "#28a745", "red": "#d9534f",
            "dark": "#181818", "input": "#3e3e42", "turbo": "#d32f2f"
        }
        
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground="white", font=("Segoe UI", 10))
        style.configure("TButton", background="#333", foreground="white", borderwidth=0, font=("Segoe UI", 9))
        style.map("TButton", background=[("active", self.colors["accent"])])
        style.configure("Treeview", background=self.colors["panel"], foreground="white", fieldbackground=self.colors["panel"], font=("Consolas", 10), rowheight=25)
        style.configure("Treeview.Heading", background="#333", foreground="white", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", self.colors["accent"])])

    def create_gui(self):
        # ÜST PANEL
        top_frame = tk.Frame(self.root, bg=self.colors["panel"], pady=10, padx=10)
        top_frame.pack(fill="x")
        
        tk.Label(top_frame, text="SHADOW MACRO V6", font=("Segoe UI", 16, "bold"), fg=self.colors["accent"], bg=self.colors["panel"]).pack(side="left")
        
        win_frame = tk.Frame(top_frame, bg=self.colors["panel"])
        win_frame.pack(side="right")
        self.cb_window = ttk.Combobox(win_frame, textvariable=self.target_window, width=25, state="readonly")
        self.cb_window.pack(side="left", padx=5)
        tk.Button(win_frame, text="🔄", width=3, command=self.refresh_windows, bg="#444").pack(side="left")
        ttk.Checkbutton(win_frame, text="Pencere Modu", variable=self.use_window_mode).pack(side="left", padx=10)

        # ORTA PANEL
        mid_frame = tk.Frame(self.root, bg=self.colors["bg"], pady=10, padx=10)
        mid_frame.pack(fill="both", expand=True)

        # SOL: TABLO
        table_frame = tk.Frame(mid_frame, bg=self.colors["bg"])
        table_frame.pack(side="left", fill="both", expand=True)
        cols = ("ID", "Type", "Detail", "Delay")
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings', selectmode="browse")
        self.tree.heading("ID", text="#"); self.tree.column("ID", width=30, anchor="center")
        self.tree.heading("Type", text="İşlem Tipi"); self.tree.column("Type", width=80)
        self.tree.heading("Detail", text="Detay"); self.tree.column("Detail", width=200)
        self.tree.heading("Delay", text="Süre"); self.tree.column("Delay", width=60, anchor="center")
        scroll = tk.Scrollbar(table_frame, command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        
        tbl_btns = tk.Frame(table_frame, bg=self.colors["bg"], pady=5)
        tbl_btns.pack(fill="x", side="bottom")
        tk.Button(tbl_btns, text="⬆", width=3, bg="#444", command=lambda: self.move_row(-1)).pack(side="left", padx=1)
        tk.Button(tbl_btns, text="⬇", width=3, bg="#444", command=lambda: self.move_row(1)).pack(side="left", padx=1)
        tk.Button(tbl_btns, text="❌ Sil", bg=self.colors["red"], command=self.delete_row).pack(side="right")

        # SAĞ: EDİTÖR
        editor_frame = tk.LabelFrame(mid_frame, text=" İşlem Editörü ", bg="#2d2d30", fg="#aaa", font=("Segoe UI", 10, "bold"), width=300, height=400)
        editor_frame.pack(side="right", fill="y", padx=(10,0))
        editor_frame.pack_propagate(False)

        tk.Label(editor_frame, text="İşlem Tipi:", bg="#2d2d30", fg="white").pack(anchor="w", padx=10, pady=(10,0))
        self.cb_type = ttk.Combobox(editor_frame, textvariable=self.manual_type, values=["Click", "Press", "Scroll"], state="readonly")
        self.cb_type.pack(fill="x", padx=10, pady=5)
        self.cb_type.bind("<<ComboboxSelected>>", self.update_editor_ui)

        self.dynamic_frame = tk.Frame(editor_frame, bg="#2d2d30")
        self.dynamic_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_pick = tk.Button(editor_frame, text="🎯 Konum Seç (X Tuşu ile)", bg="#ff9800", fg="black", font=("Segoe UI", 10, "bold"), command=self.start_picker)

        tk.Label(editor_frame, text="Bekleme Süresi (sn):", bg="#2d2d30", fg="white").pack(anchor="w", padx=10, pady=(10,0))
        self.ent_delay = tk.Entry(editor_frame, bg=self.colors["input"], fg="white")
        self.ent_delay.insert(0, "0.05") # Hız için varsayılanı düşürdük
        self.ent_delay.pack(fill="x", padx=10, pady=5)

        tk.Button(editor_frame, text="➕ Listeye Ekle", bg=self.colors["green"], font=("Segoe UI", 11, "bold"), command=self.add_manual_action).pack(fill="x", padx=10, pady=20)
        
        tk.Frame(editor_frame, height=1, bg="#444").pack(fill="x", pady=10)
        self.btn_rec = tk.Button(editor_frame, text="🔴 CANLI KAYIT (REC)", bg=self.colors["red"], font=("Segoe UI", 10, "bold"), command=self.toggle_recording)
        self.btn_rec.pack(fill="x", padx=10)

        # ALT PANEL: KONTROLLER
        bot_frame = tk.Frame(self.root, bg="#181818", pady=15, padx=20)
        bot_frame.pack(fill="x", side="bottom")

        self.btn_play = tk.Button(bot_frame, text="▶ BAŞLAT (F6)", bg=self.colors["accent"], font=("Segoe UI", 14, "bold"), width=20, command=self.start_macro_thread)
        self.btn_play.pack(side="left")
        
        set_frame = tk.Frame(bot_frame, bg="#181818")
        set_frame.pack(side="right")
        tk.Label(set_frame, text="Tekrar:", bg="#181818").pack(side="left")
        tk.Entry(set_frame, textvariable=self.loop_count, width=5, bg="#333", fg="white").pack(side="left", padx=5)
        
        # TURBO MODE CHECKBOX
        ttk.Checkbutton(set_frame, text="⚡ TURBO MOD (Riskli)", variable=self.use_turbo_mode, command=self.toggle_turbo_warning).pack(side="left", padx=10)
        ttk.Checkbutton(set_frame, text="Anti-Bot", variable=self.human_speed).pack(side="left", padx=10)
        
        self.status_bar = tk.Label(self.root, text="Sistem Hazır", bg="#007acc", anchor="w", padx=10)
        self.status_bar.pack(side="bottom", fill="x")
        
        self.input_widgets = {}
        self.update_editor_ui(None)
        self.refresh_windows()

    # --- HIZLI TIKLAMA (CTYPES) ---
    def fast_click(self, x, y, button="left"):
        # Mouse'u ışınla (Pyautogui'den çok daha hızlı)
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        
        down_event = MOUSEEVENTF_LEFTDOWN
        up_event = MOUSEEVENTF_LEFTUP
        
        if button == "right":
            down_event = MOUSEEVENTF_RIGHTDOWN
            up_event = MOUSEEVENTF_RIGHTUP
        elif button == "middle":
            down_event = MOUSEEVENTF_MIDDLEDOWN
            up_event = MOUSEEVENTF_MIDDLEUP

        # Tıkla ve Bırak (Arada gecikme yok)
        ctypes.windll.user32.mouse_event(down_event, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(up_event, 0, 0, 0, 0)

    def toggle_turbo_warning(self):
        if self.use_turbo_mode.get():
            messagebox.showwarning("Turbo Mod", "Bu mod Windows API'sini doğrudan kullanır.\nCPS 50-100 üzerine çıkabilir.\nOyunlar bunu hile olarak algılayabilir.\nEğer durduramazsan mouse'u sol üste çek!")

    # --- EDİTÖR MANTIĞI ---
    def update_editor_ui(self, event):
        for widget in self.dynamic_frame.winfo_children(): widget.destroy()
        self.btn_pick.pack_forget()
        atype = self.manual_type.get()
        if atype == "Click":
            row1 = tk.Frame(self.dynamic_frame, bg="#2d2d30"); row1.pack(fill="x")
            tk.Label(row1, text="X:", bg="#2d2d30").pack(side="left")
            self.input_widgets["x"] = tk.Entry(row1, textvariable=self.temp_x, width=8, bg=self.colors["input"], fg="white"); self.input_widgets["x"].pack(side="left", padx=5)
            tk.Label(row1, text="Y:", bg="#2d2d30").pack(side="left")
            self.input_widgets["y"] = tk.Entry(row1, textvariable=self.temp_y, width=8, bg=self.colors["input"], fg="white"); self.input_widgets["y"].pack(side="left", padx=5)
            
            tk.Label(self.dynamic_frame, text="Mouse Butonu:", bg="#2d2d30", fg="white").pack(anchor="w", pady=(5,0))
            self.input_widgets["btn"] = ttk.Combobox(self.dynamic_frame, values=["left", "right", "middle"], state="readonly"); self.input_widgets["btn"].current(0); self.input_widgets["btn"].pack(fill="x")
            self.btn_pick.pack(fill="x", padx=10, pady=5, in_=self.dynamic_frame.master)
        elif atype == "Press":
            tk.Label(self.dynamic_frame, text="Basılacak Tuş:", bg="#2d2d30").pack(anchor="w")
            self.input_widgets["key"] = tk.Entry(self.dynamic_frame, bg=self.colors["input"], fg="white"); self.input_widgets["key"].pack(fill="x")
        elif atype == "Scroll":
             tk.Label(self.dynamic_frame, text="Miktar (+/-):", bg="#2d2d30").pack(anchor="w")
             self.input_widgets["scroll"] = tk.Entry(self.dynamic_frame, bg=self.colors["input"], fg="white"); self.input_widgets["scroll"].insert(0, "-100"); self.input_widgets["scroll"].pack(fill="x")

    def start_picker(self):
        self.is_picking = True
        self.btn_pick.config(text="🖱️ 'X' TUŞUNA BAS", bg="#00e676")

    def on_picker_key(self, key):
        if self.is_picking:
            try:
                if isinstance(key, KeyCode) and key.char == 'x':
                    x, y = pyautogui.position()
                    if self.use_window_mode.get():
                        win = self.get_target_window()
                        if win: x -= win.left; y -= win.top
                    self.temp_x.set(x); self.temp_y.set(y)
                    self.is_picking = False
                    self.root.after(0, self.reset_picker_btn)
            except AttributeError: pass

    def reset_picker_btn(self):
        self.btn_pick.config(text="🎯 Konum Seç (X Tuşu ile)", bg="#ff9800")

    def add_manual_action(self):
        try:
            delay = float(self.ent_delay.get())
            atype = self.manual_type.get()
            act = {"type": atype, "delay": delay}
            if atype == "Click":
                act["x"] = self.temp_x.get(); act["y"] = self.temp_y.get(); act["btn"] = self.input_widgets["btn"].get()
                detail = f"Click [{act['btn']}] @ {act['x']},{act['y']}"
            elif atype == "Press":
                act["key"] = self.input_widgets["key"].get(); detail = f"Press Key: {act['key']}"
            elif atype == "Scroll":
                act["amount"] = int(self.input_widgets["scroll"].get()); detail = f"Scroll: {act['amount']}"
            self.actions.append(act); self.refresh_table()
        except ValueError: messagebox.showerror("Hata", "Sayısal değer hatası.")

    def refresh_table(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, act in enumerate(self.actions):
            desc = ""
            if act["type"] == "Click": desc = f"X:{act['x']} Y:{act['y']} ({act['btn']})"
            elif act["type"] == "Press": desc = f"Key: {act['key']}"
            elif act["type"] == "Scroll": desc = f"Val: {act['amount']}"
            self.tree.insert("", "end", values=(i+1, act["type"], desc, f"{act['delay']}s"))

    def delete_row(self):
        sel = self.tree.selection()
        if sel: del self.actions[self.tree.index(sel[0])]; self.refresh_table()
        
    def move_row(self, direction):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0]); new_idx = idx + direction
        if 0 <= new_idx < len(self.actions):
            self.actions[idx], self.actions[new_idx] = self.actions[new_idx], self.actions[idx]
            self.refresh_table(); self.tree.selection_set(self.tree.get_children()[new_idx])

    def refresh_windows(self):
        try: self.cb_window['values'] = sorted([w.title for w in gw.getAllWindows() if w.title.strip()])
        except: pass

    def get_target_window(self):
        title = self.target_window.get()
        if not title: return None
        try: return gw.getWindowsWithTitle(title)[0]
        except: return None

    # --- BOT MOTORU ---
    def start_hotkey_listener(self):
        threading.Thread(target=lambda: keyboard.GlobalHotKeys({'<f6>': self.toggle_bot}).start(), daemon=True).start()
        
    def toggle_bot(self):
        if self.is_running: self.is_running = False; self.status_bar.config(text="Bot Durduruldu", bg=self.colors["red"])
        else: self.start_macro_thread()

    def start_macro_thread(self):
        if not self.actions: return
        self.is_running = True
        self.status_bar.config(text="Bot Çalışıyor... (F6 ile Durdur)", bg=self.colors["green"])
        threading.Thread(target=self.run_bot).start()

    def run_bot(self):
        loops = self.loop_count.get()
        cnt = 0
        
        # Pyautogui güvenliğini Turbo Mod'da devre dışı bırakmak gerekebilir ama riskli.
        # Biz manuel kontrolde tutalım.
        
        while self.is_running:
            if loops > 0 and cnt >= loops: break
            
            # Pencere Konumu
            win_offset_x, win_offset_y = 0, 0
            if self.use_window_mode.get():
                win = self.get_target_window()
                if win: 
                    # Pencere küçültülmüşse geri getir
                    if win.isMinimized: 
                        try: win.restore()
                        except: pass
                    win_offset_x, win_offset_y = win.left, win.top

            for act in self.actions:
                if not self.is_running: break
                
                # SÜRE YÖNETİMİ (TURBO MOD FARKI)
                delay = act["delay"]
                
                if self.use_turbo_mode.get():
                    # Turbo modda anti-bot kapatılır ve süre minimuma indirilir
                    if delay < 0.01: 
                        # Neredeyse hiç bekleme
                        pass 
                    else:
                        time.sleep(delay)
                else:
                    # Normal Mod
                    if self.human_speed.get(): delay *= random.uniform(0.8, 1.2)
                    time.sleep(delay)
                
                try:
                    if act["type"] == "Click":
                        tx = act["x"] + win_offset_x
                        ty = act["y"] + win_offset_y
                        
                        # Anti-Bot Titreme (Sadece normal modda)
                        if self.human_speed.get() and not self.use_turbo_mode.get():
                            tx += random.randint(-2, 2)
                            ty += random.randint(-2, 2)
                        
                        # HANGİ YÖNTEM?
                        if self.use_turbo_mode.get():
                            # CTYPES (Hızlı)
                            self.fast_click(tx, ty, act["btn"])
                        else:
                            # PYAUTOGUI (Yavaş/Güvenli)
                            pyautogui.click(tx, ty, button=act["btn"])
                        
                    elif act["type"] == "Press":
                        pyautogui.press(act["key"])
                        
                    elif act["type"] == "Scroll":
                        pyautogui.scroll(act["amount"])
                        
                except Exception as e:
                    print(e)
            
            cnt += 1
        self.is_running = False
        self.status_bar.config(text="İşlem Bitti", bg="#007acc")

    # --- KAYIT SİSTEMİ ---
    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.btn_rec.config(text="🔴 CANLI KAYIT (REC)", bg=self.colors["red"])
            if self.mouse_listener: self.mouse_listener.stop()
            if self.keyboard_listener: self.keyboard_listener.stop()
        else:
            self.is_recording = True
            self.btn_rec.config(text="⏹ KAYDI BİTİR (ESC)", bg="#333")
            self.actions = []
            self.refresh_table()
            self.mouse_listener = mouse.Listener(on_click=self.on_click)
            self.keyboard_listener = keyboard.Listener(on_release=self.on_key)
            self.mouse_listener.start()
            self.keyboard_listener.start()
            self.start_time = time.time()

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            delay = round(time.time() - self.start_time, 3) # Daha hassas süre
            self.start_time = time.time()
            if self.use_window_mode.get():
                win = self.get_target_window()
                if win: x -= win.left; y -= win.top
            self.actions.append({"type": "Click", "x": x, "y": y, "btn": str(button).replace("Button.",""), "delay": delay})
            self.root.after(0, self.refresh_table)

    def on_key(self, key):
        if key == Key.esc: self.toggle_recording(); return False
        if self.is_recording and key != Key.f6:
            delay = round(time.time() - self.start_time, 3)
            self.start_time = time.time()
            try: k = key.char
            except: k = str(key).replace("Key.", "")
            self.actions.append({"type": "Press", "key": k, "delay": delay})
            self.root.after(0, self.refresh_table)

if __name__ == "__main__":
    root = tk.Tk()
    app = ShadowMacroV6(root)
    root.mainloop()
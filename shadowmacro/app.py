"""Ana uygulama sınıfı: mixin'leri birleştirir, durumu ve dinleyicileri kurar."""
import os
import queue
import tkinter as tk

from pynput import keyboard
from pynput.keyboard import Key

from .actions import TYPE_LABELS
from .config import ConfigMixin
from .core.cv import HAS_CV
from .core.windows import _get_all_windows, _get_window_rect
from .core.winapi import user32, winmm, GA_ROOT
from .engine.clicker import ClickerMixin
from .engine.executor import ExecutorMixin
from .engine.recorder import RecorderMixin
from .engine.runner import RunnerMixin
from .engine.runtime import RuntimeMixin
from .ui.action_list import ActionListMixin
from .ui.editor import EditorMixin
from .ui.layout import LayoutMixin
from .ui.picker import PickerMixin
from .ui.status import StatusMixin
from .ui.theme import BG
from .ui.view import ViewMixin
from .ui.widgets import WidgetsMixin


class ShadowMacroV12(WidgetsMixin, LayoutMixin, ViewMixin, EditorMixin, StatusMixin, ActionListMixin,
                     PickerMixin, RunnerMixin, RuntimeMixin, ExecutorMixin, ClickerMixin, RecorderMixin, ConfigMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("ShadowMacro V12")
        self.root.geometry("1280x880")
        self.root.minsize(1140, 780)
        self.root.configure(fg_color=BG)

        # --- DURUM ---
        self.is_macro_running = False
        self.is_paused = False
        self.is_f7_running = False
        self.is_recording = False
        self.is_picking = False
        self.editing_index = None

        self.actions = []
        self.mouse_listener = None
        self.rec_kb_listener = None
        self._held = set()
        self._run_info = {}
        self._cur_idx = None
        self._shown_idx = None
        self._log_q = queue.Queue()
        self._tmpl_cache = {}
        self._f7_hwnd = None
        self._f7_pos = (0, 0)
        self._f7_window_mode = False
        self._f7_interval = 0.1
        self._f7_turbo = False
        self._f7_human = True
        self._status_after = None
        self._preview_img = None
        self._pick_target = None

        # --- DEĞİŞKENLER ---
        self.loop_var = tk.StringVar(value="0")
        self.limit_var = tk.StringVar(value="0")
        self.start_delay_var = tk.StringVar(value="0")
        self.human_speed = tk.BooleanVar(value=True)
        self.use_turbo_mode = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)
        self.use_window_mode = tk.BooleanVar(value=False)
        self.target_window_title = tk.StringVar()

        self.f7_cps = 10.0
        self.cps_text = tk.StringVar(value="10")
        self.type_var = tk.StringVar(value=TYPE_LABELS["Click"])
        self.delay_var = tk.StringVar(value="0.1")
        self.fv = {}  # editör alan değişkenleri (tipler arası korunur)

        # Windows zamanlayıcı çözünürlüğünü 1 ms'ye çek (yüksek CPS için şart)
        winmm.timeBeginPeriod(1)

        self.setup_styles()
        self.create_gui()
        self.load_config()
        self.refresh_windows()
        self.refresh_tree()
        self.update_status_pill()

        self.root.update_idletasks()
        self._own_hwnd = user32.GetAncestor(int(self.root.wm_frame(), 16), GA_ROOT)

        self.start_hotkey_listener()
        self.picker_listener = keyboard.Listener(on_release=self.on_picker_key)
        self.picker_listener.daemon = True
        self.picker_listener.start()
        self._track_cursor()
        self._poll()
        if not HAS_CV:
            self.log("Uyarı: opencv-python/numpy kurulu değil — Resim Bul ve Renk Ara çalışmaz.")

    # ================= PENCERE YÖNETİMİ =================
    def refresh_windows(self):
        try:
            own = self.root.title()
            wins = sorted(w for w in _get_all_windows() if w != own)
            self.cb_window.configure(values=wins)
            cur = self.target_window_title.get()
            if cur and cur not in wins:
                self.set_status(f"“{cur}” penceresi şu an açık değil.", "warn", 4000)
            else:
                self.set_status(f"{len(wins)} pencere bulundu.", "info", 2500)
        except Exception:
            pass
        self.update_mode_hint()

    def get_window_rect(self):
        title = self.target_window_title.get()
        if not title:
            return None
        return _get_window_rect(title)

    # ================= KISAYOLLAR =================
    def start_hotkey_listener(self):
        def on_press(key):
            if key == Key.f6: self.root.after(0, self.toggle_macro)
            elif key == Key.f7: self.root.after(0, self.toggle_f7_clicker)
            elif key == Key.f8: self.root.after(0, self.toggle_pause)
        self.hotkey_listener = keyboard.Listener(on_press=on_press)
        self.hotkey_listener.daemon = True
        self.hotkey_listener.start()

    # ================= PENCERE AYARLARI / KAPANIŞ =================
    def toggle_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    def on_close(self):
        self.is_macro_running = False
        self.is_f7_running = False
        self._release_all()
        self.save_config()
        winmm.timeEndPeriod(1)
        self.root.destroy()
        os._exit(0)

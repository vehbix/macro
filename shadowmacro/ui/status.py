"""Durum çubuğu, günlük, durum rozeti ve periyodik arayüz güncellemesi."""
import queue
import time

from ..core.utils import _cursor_pos
from .theme import SURFACE2, TEXT, MUTED, ACCENT, ACCENT_H, GREEN, RED, RED_H, AMBER, AMBER_H


class StatusMixin:
    # ================= UI DURUMU =================
    def set_status(self, text, kind="info", timeout=None):
        color = {"info": MUTED, "ok": GREEN, "error": RED, "warn": AMBER}[kind]
        self.lbl_status.configure(text=text, text_color=color)
        if self._status_after:
            self.root.after_cancel(self._status_after)
            self._status_after = None
        if timeout:
            def expire():
                self._status_after = None
                self.lbl_status.configure(text="", text_color=MUTED)
            self._status_after = self.root.after(timeout, expire)

    def log(self, msg):
        """Thread-safe: herhangi bir thread'den çağrılabilir."""
        self._log_q.put(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def update_status_pill(self):
        if self.is_recording:
            text, fg, bg = "● Kayıt yapılıyor", RED, "#3a2328"
        elif self.is_macro_running and self.is_paused:
            text, fg, bg = "❚❚ Duraklatıldı", AMBER, "#3a2f1a"
        elif self.is_macro_running:
            text, fg, bg = "● Makro çalışıyor", ACCENT, "#1d2540"
        elif self.is_f7_running:
            text, fg, bg = "● Tıklayıcı aktif", AMBER, "#3a2f1a"
        else:
            text, fg, bg = "● Hazır", GREEN, "#163328"
        self.status_pill.configure(text=text, text_color=fg, fg_color=bg)

    def update_mode_hint(self):
        if self.use_window_mode.get():
            if self.target_window_title.get():
                self.lbl_mode_hint.configure(text="Açık · Fare ve klavye kullanılmaz, komutlar seçili pencereye sinyal olarak gider.", text_color=GREEN)
            else:
                self.lbl_mode_hint.configure(text="Açık · Önce bir hedef pencere seç.", text_color=AMBER)
        else:
            self.lbl_mode_hint.configure(text="Kapalı · Gerçek fare ve klavye kullanılır (oyunlarla en uyumlu mod).", text_color=MUTED)

    def _set_play_button(self, running):
        if running:
            self.btn_play.configure(text="⏹  Durdur   (F6)", fg_color=RED, hover_color=RED_H, text_color="white")
            self.btn_pause.configure(state="normal")
        else:
            self.btn_play.configure(text="▶  Makroyu Başlat   (F6)", fg_color=ACCENT, hover_color=ACCENT_H, text_color="white")
            self.btn_pause.configure(state="disabled", text="❚❚  Duraklat", fg_color=SURFACE2, text_color=TEXT)

    def _set_f7_ui(self, running):
        if running:
            self.btn_f7.configure(text="⏹  Durdur", fg_color=RED, hover_color=RED_H, text_color="white")
            self.lbl_f7_status.configure(text="● Aktif", text_color=AMBER)
        else:
            self.btn_f7.configure(text="▶  Başlat", fg_color=AMBER, hover_color=AMBER_H, text_color="#1f1606")
            self.lbl_f7_status.configure(text="● Durdu", text_color=MUTED)
        self.update_status_pill()

    def _track_cursor(self):
        try:
            x, y = _cursor_pos()
            suffix = ""
            if self.use_window_mode.get():
                win = self.get_window_rect()
                if win:
                    x -= win.left; y -= win.top
                    suffix = "  (pencereye göre)"
            self.lbl_cursor.configure(text=f"İmleç  X {x:>5}  Y {y:>5}{suffix}")
        except Exception:
            pass
        self.root.after(100, self._track_cursor)

    def _poll(self):
        # günlük
        lines = []
        try:
            while len(lines) < 300:
                lines.append(self._log_q.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", "".join(lines))
            count = int(self.log_box.index("end-1c").split(".")[0])
            if count > 1000:
                self.log_box.delete("1.0", f"{count - 1000}.0")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        # çalışan satır vurgusu + durum metni
        idx = self._cur_idx if self.is_macro_running else None
        if idx != self._shown_idx:
            children = self.tree.get_children()
            if self._shown_idx is not None and self._shown_idx < len(children):
                self.tree.item(children[self._shown_idx], tags=self._row_tags(self._shown_idx))
            if idx is not None and idx < len(children):
                self.tree.item(children[idx], tags=self._row_tags(idx) + ("running",))
                self.tree.see(children[idx])
            self._shown_idx = idx
        if self.is_macro_running and self._status_after is None:
            info = self._run_info
            if info.get("countdown"):
                self.lbl_status.configure(text=f"Başlıyor: {info['countdown']} …", text_color=AMBER)
            elif info.get("start"):
                el = int(time.time() - info["start"])
                total = f"/{info['loops']}" if info.get("loops") else ""
                pause = "  ·  DURAKLATILDI (F8 ile devam)" if self.is_paused else ""
                self.lbl_status.configure(
                    text=f"Makro çalışıyor · tur {info.get('loop', 1)}{total} · adım #{(info.get('pc') or 0) + 1}"
                         f" · {el // 60:02d}:{el % 60:02d}{pause}",
                    text_color=AMBER if self.is_paused else MUTED)
        self.root.after(100, self._poll)

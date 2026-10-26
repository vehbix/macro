"""Aksiyon listesi: ekleme, düzenleme, sıralama ve proje dosyası aç/kaydet."""
import json
import os
from tkinter import messagebox, filedialog

from ..actions import TYPE_LABELS, BTN, KEYMODE, UNTIL, FOUNDCLICK, _choice_label, _outcome_text, _normalize
from ..core.utils import _fmt_delay
from .theme import SURFACE2, TEXT, ACCENT, ACCENT_H


class ActionListMixin:
    # ================= LİSTE İŞLEMLERİ =================
    def add_action(self):
        try:
            act = self._editor_action()
        except ValueError as e:
            self.set_status(str(e), "error", 5000)
            return
        act["enabled"] = True
        sel = self._selected_index()
        idx = len(self.actions) if sel is None else sel + 1
        self.actions.insert(idx, act)
        self.refresh_tree()
        self._select(idx)
        self.set_status(f"{TYPE_LABELS[act['type']].split()[-1]} aksiyonu #{idx + 1} olarak eklendi.", "ok", 2500)

    def update_action(self):
        idx = self.editing_index
        if idx is None or idx >= len(self.actions):
            return
        try:
            act = self._editor_action()
        except ValueError as e:
            self.set_status(str(e), "error", 5000)
            return
        old = self.actions[idx]
        act["enabled"] = old.get("enabled", True)
        # etiket adı değiştiyse ona giden Git/sonuçları da güncelle
        if old["type"] == "Label" and act["type"] == "Label" and old.get("name") != act["name"]:
            self._rename_label(old.get("name"), act["name"])
        self.actions[idx] = act
        self.refresh_tree()
        self._select(idx)
        self.set_status(f"#{idx + 1} güncellendi.", "ok", 2500)

    def _rename_label(self, old, new):
        for a in self.actions:
            if a["type"] == "Goto" and a.get("label") == old:
                a["label"] = new
            for k in ("on_timeout", "on_true", "on_false", "on_found", "on_missing"):
                if a.get(k) == f"goto:{old}":
                    a[k] = f"goto:{new}"

    def on_tree_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            self.editing_index = None
            self.lbl_editor_title.configure(text="Yeni Aksiyon")
            self.btn_update.configure(state="disabled", fg_color=SURFACE2, text_color=TEXT)
            self._update_editor_hint()
            return
        idx = self.tree.index(sel[0])
        if idx >= len(self.actions):
            return
        self.editing_index = idx
        self._load_into_editor(self.actions[idx])
        self.lbl_editor_title.configure(text=f"Aksiyon #{idx + 1}")
        self.btn_update.configure(state="normal", fg_color=ACCENT, hover_color=ACCENT_H, text_color="white")
        self._update_editor_hint()

    def clear_selection(self):
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self.on_tree_select()

    def _select(self, idx):
        children = self.tree.get_children()
        if 0 <= idx < len(children):
            self.tree.selection_set(children[idx])
            self.tree.see(children[idx])

    def _selected_index(self):
        sel = self.tree.selection()
        return self.tree.index(sel[0]) if sel else None

    def _detail(self, a):
        t = a["type"]
        xy = f"{a.get('x')}, {a.get('y')}"
        if t == "Click":
            s = f"{_choice_label(BTN, a['button'])}{' çift' if a.get('double') else ''} tık"
            s += "  ·  imleç konumunda" if a.get("here") else f"  @  {xy}"
            if a.get("hold"): s += f"  ·  {a['hold']:g} sn basılı"
            return s
        if t == "Move":
            return f"göreli  {a['x']:+d}, {a['y']:+d}" if a.get("relative") else f"→  {xy}"
        if t == "Drag":
            return f"{xy}  →  {a['x2']}, {a['y2']}  ·  {_choice_label(BTN, a['button'])}"
        if t == "Press":
            s = a.get("key", "")
            if a.get("mode") != "tap": s += f"  ·  {_choice_label(KEYMODE, a['mode']).lower()}"
            elif a.get("hold"): s += f"  ·  {a['hold']:g} sn basılı"
            return s
        if t == "Type":
            txt = a.get("text", "")
            return f"“{txt[:40]}{'…' if len(txt) > 40 else ''}”"
        if t == "Scroll":
            return f"{a['amount']:+d}"
        if t == "Wait":
            return "bekle"
        if t == "WaitColor":
            s = f"RGB({a['color']}) @ {xy}  ·  {_choice_label(UNTIL, a['until']).lower()}  ·  ≤ {a['timeout']:g} sn"
            if a.get("on_timeout", "next") != "next": s += f"  ·  aşılırsa {_outcome_text(a['on_timeout'])}"
            return s
        if t == "IfColor":
            return f"RGB({a['color']}) @ {xy}  ?  {_outcome_text(a['on_true'])}  :  {_outcome_text(a['on_false'])}"
        if t in ("FindImage", "FindColor"):
            what = f"resim {a.get('img_w', 0)}×{a.get('img_h', 0)}" if t == "FindImage" else f"RGB({a['color']})"
            s = f"{what}  ·  {_choice_label(FOUNDCLICK, a['click']).lower()}"
            if a.get("timeout"): s += f"  ·  ≤ {a['timeout']:g} sn"
            if a.get("on_found", "next") != "next": s += f"  ·  varsa {_outcome_text(a['on_found'])}"
            if a.get("on_missing", "next") != "next": s += f"  ·  yoksa {_outcome_text(a['on_missing'])}"
            return s
        if t == "Label":
            return a.get("name", "")
        if t == "Goto":
            return f"→  {a.get('label', '')}" + (f"  ·  {a['times']} kez" if a.get("times") else "  ·  her zaman")
        if t == "Notify":
            s = a.get("text", "") or "(mesajsız)"
            if a.get("beep"): s += "  ·  🔊"
            if a.get("stop"): s += "  ·  durdurur"
            return s
        return ""

    def _row_tags(self, i):
        a = self.actions[i]
        tags = ["odd"] if i % 2 else []
        if a["type"] == "Label": tags.append("label")
        elif a["type"] in ("Goto", "IfColor"): tags.append("flow")
        if not a.get("enabled", True): tags.append("disabled")
        return tuple(tags)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self._shown_idx = None
        for i, a in enumerate(self.actions):
            t = a["type"]
            if t == "Label":
                delay = ""
            elif t in ("WaitColor",):
                delay = _fmt_delay(a.get("delay", 0)) if a.get("delay") else "—"
            else:
                delay = _fmt_delay(a.get("delay", 0))
            on = "●" if a.get("enabled", True) else "○"
            self.tree.insert("", "end", values=(i + 1, on, TYPE_LABELS.get(t, t), self._detail(a), delay),
                             tags=self._row_tags(i))
        self.lbl_count.configure(text=str(len(self.actions)))
        if self.actions:
            self.lbl_empty.place_forget()
        else:
            self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")

    def delete_row(self):
        idx = self._selected_index()
        if idx is None:
            self.set_status("Silmek için listeden bir satır seç.", "warn", 2500)
            return
        del self.actions[idx]
        self.refresh_tree()
        if self.actions:
            self._select(min(idx, len(self.actions) - 1))
        else:
            self.clear_selection()

    def duplicate_row(self):
        idx = self._selected_index()
        if idx is None:
            self.set_status("Çoğaltmak için listeden bir satır seç.", "warn", 2500)
            return
        copy = dict(self.actions[idx])
        if copy["type"] == "Label":
            base, n = copy["name"], 2
            while f"{base} {n}" in self._labels():
                n += 1
            copy["name"] = f"{base} {n}"
        self.actions.insert(idx + 1, copy)
        self.refresh_tree()
        self._select(idx + 1)

    def toggle_enabled(self):
        idx = self._selected_index()
        if idx is None:
            self.set_status("Açıp kapatmak için listeden bir satır seç.", "warn", 2500)
            return
        a = self.actions[idx]
        a["enabled"] = not a.get("enabled", True)
        self.refresh_tree()
        self._select(idx)
        self.set_status(f"#{idx + 1} {'açıldı' if a['enabled'] else 'devre dışı bırakıldı (atlanır)'}.", "info", 2500)

    def move_row(self, d):
        idx = self._selected_index()
        if idx is None: return
        n = idx + d
        if 0 <= n < len(self.actions):
            self.actions[idx], self.actions[n] = self.actions[n], self.actions[idx]
            self.refresh_tree()
            self._select(n)

    def clear_all(self):
        if not self.actions: return
        if messagebox.askyesno("Temizle", f"{len(self.actions)} aksiyonun tamamı silinsin mi?"):
            self.actions.clear()
            self.refresh_tree()
            self.clear_selection()

    def save_project(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Makro", "*.json")])
        if f:
            with open(f, 'w', encoding="utf-8") as file: json.dump(self.actions, file, indent=2, ensure_ascii=False)
            self.set_status(f"Kaydedildi: {os.path.basename(f)}", "ok", 3000)

    def load_project(self):
        f = filedialog.askopenfilename(filetypes=[("Makro", "*.json"), ("Tümü", "*.*")])
        if not f:
            return
        try:
            with open(f, 'r', encoding="utf-8") as file:
                raw = json.load(file)
            acts = [n for n in (_normalize(a) for a in raw) if n]
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya açılamadı:\n{e}")
            return
        self.actions = acts
        self.refresh_tree()
        self.clear_selection()
        skipped = len(raw) - len(acts)
        msg = f"Açıldı: {os.path.basename(f)} · {len(acts)} aksiyon"
        if skipped:
            msg += f" ({skipped} tanınmayan satır atlandı)"
        self.set_status(msg, "ok", 4000)

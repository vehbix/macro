"""Aksiyon editörü: şemaya göre form üretme, okuma ve doldurma."""
import math
import tkinter as tk

import customtkinter as ctk

from ..actions import SCHEMA, XY_KEYS, TYPE_LABELS, TYPE_FROM_LABEL, _choice_label, _choice_value
from ..core.cv import HAS_CV
from ..core.utils import _parse_keys, _parse_delay, _parse_rgb
from .theme import SURFACE2, SURFACE3, BORDER, TEXT, MUTED, ACCENT, ACCENT_H, AMBER, FONT


class EditorMixin:
    # ================= EDİTÖR FORMU =================
    def _var(self, key, kind="text", default=""):
        if key not in self.fv:
            if kind == "bool":
                self.fv[key] = tk.BooleanVar(value=bool(default))
            else:
                self.fv[key] = tk.StringVar(value="" if default is None else
                                            (f"{default:g}" if isinstance(default, float) else str(default)))
        return self.fv[key]

    @staticmethod
    def _fkey(atype, key, kind):
        """Konum, renk ve resim tipler arasında ortak; diğer alanlar her tipe özel."""
        return key if kind in ("xy", "color", "image") else f"{atype}.{key}"

    def _labels(self):
        return [a.get("name", "") for a in self.actions if a["type"] == "Label" and a.get("name")]

    def _outcome_options(self):
        return ["Devam et", "Makroyu durdur"] + [f"→ {n}" for n in self._labels()]

    @staticmethod
    def _outcome_to_display(v):
        if v == "stop": return "Makroyu durdur"
        if isinstance(v, str) and v.startswith("goto:"): return f"→ {v[5:]}"
        return "Devam et"

    @staticmethod
    def _display_to_outcome(s):
        if s == "Makroyu durdur": return "stop"
        if s.startswith("→ "): return "goto:" + s[2:]
        return "next"

    def current_type(self):
        return TYPE_FROM_LABEL.get(self.type_var.get(), "Click")

    def on_type_change(self):
        atype = self.current_type()
        for w in self.form.winfo_children():
            w.destroy()
        self._pick_buttons = {}
        self._img_preview_lbl = None
        self.is_picking = False
        row = 0

        def label(text):
            nonlocal row
            lbl = self._muted(self.form, text)
            lbl.configure(wraplength=330)
            lbl.grid(row=row, column=0, sticky="w", padx=8, pady=(8, 0))
            row += 1

        for key, text, kind, opt, default in SCHEMA[atype]:
            if kind == "xy":
                kx, ky = XY_KEYS[key]
                label(text)
                f = ctk.CTkFrame(self.form, fg_color="transparent")
                f.grid(row=row, column=0, sticky="ew", padx=8); row += 1
                f.grid_columnconfigure((1, 3), weight=1)
                self._muted(f, "X").grid(row=0, column=0, padx=(0, 6))
                self._entry(f, self._var(kx, "int", 0)).grid(row=0, column=1, sticky="ew")
                self._muted(f, "Y").grid(row=0, column=2, padx=(10, 6))
                self._entry(f, self._var(ky, "int", 0)).grid(row=0, column=3, sticky="ew")
                b = self._ghost_btn(self.form, "", None)
                b.grid(row=row, column=0, sticky="ew", padx=8, pady=(6, 0)); row += 1
                self._pick_buttons[key] = b
                self._reset_pick_button(key)
            elif kind == "color":
                label(text)
                f = ctk.CTkFrame(self.form, fg_color="transparent")
                f.grid(row=row, column=0, sticky="ew", padx=8); row += 1
                f.grid_columnconfigure(0, weight=1)
                var = self._var("color", "text", "")
                self._entry(f, var).grid(row=0, column=0, sticky="ew")
                sw = ctk.CTkFrame(f, width=32, height=32, corner_radius=8, fg_color=SURFACE2,
                                  border_width=1, border_color=BORDER)
                sw.grid(row=0, column=1, padx=(8, 0))
                self._swatch = sw
                if not getattr(self, "_color_traced", False):
                    var.trace_add("write", lambda *_: self._update_swatch())
                    self._color_traced = True
                self._update_swatch()
                b = self._ghost_btn(self.form, "", None)
                b.grid(row=row, column=0, sticky="ew", padx=8, pady=(6, 0)); row += 1
                self._pick_buttons["color"] = b
                self._reset_pick_button("color")
            elif kind == "choice":
                label(text)
                var = self._var(self._fkey(atype, key, kind), "text", _choice_label(opt, default))
                if var.get() not in [l for _, l in opt]:
                    var.set(_choice_label(opt, default))
                self._option(self.form, var, [l for _, l in opt]).grid(row=row, column=0, sticky="ew", padx=8); row += 1
            elif kind == "bool":
                var = self._var(self._fkey(atype, key, kind), "bool", default)
                ctk.CTkCheckBox(self.form, text=text, variable=var, onvalue=True, offvalue=False,
                                fg_color=ACCENT, hover_color=ACCENT_H, border_color=BORDER, text_color=TEXT,
                                font=ctk.CTkFont(FONT, 12), corner_radius=6).grid(
                    row=row, column=0, sticky="w", padx=8, pady=(10, 0)); row += 1
            elif kind in ("text", "int", "float"):
                label(f"{text}  ·  {opt}" if kind == "text" and opt else text)
                self._entry(self.form, self._var(self._fkey(atype, key, kind), kind, default)).grid(
                    row=row, column=0, sticky="ew", padx=8); row += 1
            elif kind == "outcome":
                label(text)
                var = self._var(self._fkey(atype, key, kind), "text", "Devam et")
                opts = self._outcome_options()
                if var.get() not in opts:
                    var.set("Devam et")
                self._option(self.form, var, opts).grid(row=row, column=0, sticky="ew", padx=8); row += 1
            elif kind == "labelref":
                label(text)
                var = self._var(self._fkey(atype, key, kind), "text", "")
                labels = self._labels()
                if labels and var.get() not in labels:
                    var.set(labels[0])
                if labels:
                    self._option(self.form, var, labels).grid(row=row, column=0, sticky="ew", padx=8)
                else:
                    var.set("")
                    ctk.CTkLabel(self.form, text="Önce listeye bir 🏷 Etiket ekle.", text_color=AMBER,
                                 font=ctk.CTkFont(FONT, 12)).grid(row=row, column=0, sticky="w", padx=8)
                row += 1
            elif kind == "image":
                label(text)
                self._var("image", "text", "")
                self._var("img_w", "text", "0"); self._var("img_h", "text", "0")
                prev = tk.Label(self.form, text="Resim seçilmedi", bg=SURFACE2, fg=MUTED, font=(FONT, 10),
                                height=4, bd=0)
                prev.grid(row=row, column=0, sticky="ew", padx=8, ipady=6); row += 1
                self._img_preview_lbl = prev
                self._update_image_preview()
                ctk.CTkButton(self.form, text="📷  Ekrandan Seç", command=self.capture_template, height=32,
                              corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_H,
                              font=ctk.CTkFont(FONT, 12, "bold")).grid(row=row, column=0, sticky="ew", padx=8, pady=(6, 0))
                row += 1

        if atype == "Wait":
            ctk.CTkLabel(self.form, text="Sadece aşağıdaki süre kadar bekler.\nRastgele bekleme için '1-3' gibi aralık yaz.",
                         text_color=MUTED, justify="left", font=ctk.CTkFont(FONT, 12)).grid(
                row=row, column=0, sticky="w", padx=8, pady=8)

        if atype == "Label":
            self.lbl_delay.configure(text="Etiketler beklemez, Git aksiyonları için işarettir.")
            self.ent_delay.grid_remove()
        else:
            self.ent_delay.grid()
            self.lbl_delay.configure(text="Bekleme süresi (sn) · '1-3' = rastgele aralık" if atype == "Wait"
                                     else "Öncesinde bekle (sn) · '1-3' = rastgele aralık")
        self._update_editor_hint()

    def _update_editor_hint(self):
        if self.editing_index is None:
            self.lbl_editor_hint.configure(text="Listeden bir satır seçersen burada düzenleyebilirsin. "
                                                "Satır seçiliyken Ekle, yeni aksiyonu onun altına koyar.")
        else:
            self.lbl_editor_hint.configure(text="Değiştirip Güncelle'ye bas. Ekle, kopyasını altına ekler.")

    def _reset_pick_button(self, key):
        b = self._pick_buttons.get(key)
        if not b:
            return
        text = "🎨  Renk ve Konum Seç   (X)" if key == "color" else "🎯  Konum Seç   (X)"
        if key == "xy2":
            text = "🎯  Bitiş Konumunu Seç   (X)"
        b.configure(text=text, command=lambda k=key: self.start_picker(k), fg_color=SURFACE2,
                    hover_color=SURFACE3, text_color=TEXT, border_width=1)

    def _update_swatch(self):
        sw = getattr(self, "_swatch", None)
        if not sw or not sw.winfo_exists():
            return
        try:
            r, g, b = _parse_rgb(self.fv["color"].get())
            sw.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")
        except Exception:
            sw.configure(fg_color=SURFACE2)

    def _update_image_preview(self):
        lbl = self._img_preview_lbl
        if not lbl or not lbl.winfo_exists():
            return
        data = self.fv["image"].get()
        if not data:
            lbl.configure(text="Resim seçilmedi", image="", height=4)
            return
        try:
            img = tk.PhotoImage(data=data)
            factor = max(1, math.ceil(img.width() / 320), math.ceil(img.height() / 140))
            if factor > 1:
                img = img.subsample(factor)
            self._preview_img = img
            lbl.configure(text="", image=img, height=img.height())
        except Exception:
            lbl.configure(text=f"Resim {self.fv['img_w'].get()}×{self.fv['img_h'].get()} px")

    def _editor_action(self):
        """Editördeki değerlerden aksiyon üretir; hatalıysa ValueError(mesaj)."""
        atype = self.current_type()
        act = {"type": atype}
        if atype != "Label":
            try:
                act["delay"] = _parse_delay(self.delay_var.get())
            except ValueError:
                raise ValueError("Bekleme süresi sayı (0.5) ya da aralık (1-3) olmalı.")
        else:
            act["delay"] = 0
        for key, text, kind, opt, default in SCHEMA[atype]:
            fk = self._fkey(atype, key, kind)
            if kind == "xy":
                for k in XY_KEYS[key]:
                    try:
                        act[k] = int(self.fv[k].get())
                    except ValueError:
                        raise ValueError("Koordinatlar tam sayı olmalı.")
            elif kind == "color":
                try:
                    act["color"] = ",".join(map(str, _parse_rgb(self.fv["color"].get())))
                except ValueError:
                    raise ValueError("Renk “R,G,B” biçiminde olmalı (0-255).")
            elif kind == "choice":
                act[key] = _choice_value(opt, self.fv[fk].get())
            elif kind == "bool":
                act[key] = bool(self.fv[fk].get())
            elif kind == "int":
                try:
                    act[key] = int(self.fv[fk].get())
                except ValueError:
                    raise ValueError(f"“{text}” tam sayı olmalı.")
            elif kind == "float":
                try:
                    act[key] = float(self.fv[fk].get().replace(",", "."))
                except ValueError:
                    raise ValueError(f"“{text}” sayı olmalı.")
            elif kind == "text":
                act[key] = self.fv[fk].get()
            elif kind == "outcome":
                act[key] = self._display_to_outcome(self.fv[fk].get())
            elif kind == "labelref":
                act[key] = self.fv[fk].get()
            elif kind == "image":
                act["image"] = self.fv["image"].get()
                act["img_w"] = int(self.fv["img_w"].get() or 0)
                act["img_h"] = int(self.fv["img_h"].get() or 0)

        # tipe özel kontroller
        if atype == "Press":
            try:
                _parse_keys(act["key"])
            except ValueError as e:
                raise ValueError(f"{e}. Örnek: a, enter, f5, ctrl+c")
        if atype == "Type" and not act["text"]:
            raise ValueError("Yazılacak metni gir.")
        if atype == "Label":
            name = act["name"].strip()
            if not name:
                raise ValueError("Etikete bir ad ver.")
            others = [a.get("name") for i, a in enumerate(self.actions)
                      if a["type"] == "Label" and i != self.editing_index]
            if name in others:
                raise ValueError(f"“{name}” adlı bir etiket zaten var.")
            act["name"] = name
        if atype == "Goto" and not act["label"]:
            raise ValueError("Önce listeye bir Etiket ekle.")
        if atype == "FindImage":
            if not act["image"]:
                raise ValueError("📷 Ekrandan Seç ile aranacak resmi seç.")
            if not HAS_CV:
                raise ValueError("Resim Bul için: pip install opencv-python numpy")
            if not 0.3 <= act["confidence"] <= 1.0:
                raise ValueError("Benzerlik eşiği 0.3 ile 1.0 arasında olmalı.")
        if atype == "FindColor" and not HAS_CV:
            raise ValueError("Renk Ara için: pip install opencv-python numpy")
        if atype in ("WaitColor", "IfColor", "FindColor") and not 0 <= act["tolerance"] <= 255:
            raise ValueError("Tolerans 0-255 arasında olmalı.")
        return act

    def _load_into_editor(self, a):
        atype = a["type"]
        self.type_var.set(TYPE_LABELS[atype])
        d = a.get("delay", 0)
        self.delay_var.set(d if isinstance(d, str) else f"{float(d):g}")
        for key, text, kind, opt, default in SCHEMA[atype]:
            fk = self._fkey(atype, key, kind)
            if kind == "xy":
                for k in XY_KEYS[key]:
                    self._var(k, "int", 0).set(str(a.get(k, 0)))
            elif kind == "color":
                self._var("color").set(a.get("color", ""))
            elif kind == "choice":
                self._var(fk).set(_choice_label(opt, a.get(key, default)))
            elif kind == "bool":
                self._var(fk, "bool", default).set(bool(a.get(key, default)))
            elif kind in ("int", "float"):
                v = a.get(key, default)
                self._var(fk, kind, default).set(f"{v:g}" if isinstance(v, float) else str(v))
            elif kind in ("text", "labelref"):
                self._var(fk).set(a.get(key, default) or "")
            elif kind == "outcome":
                self._var(fk).set(self._outcome_to_display(a.get(key, "next")))
            elif kind == "image":
                self._var("image").set(a.get("image", ""))
                self._var("img_w").set(str(a.get("img_w", 0)))
                self._var("img_h").set(str(a.get("img_h", 0)))
        self.on_type_change()

"""Görünüm çubuğu: panelleri göster/gizle ve yerleşimi buna göre yeniden kur."""
import tkinter as tk

import customtkinter as ctk

from .theme import SURFACE2, SURFACE3, BORDER, MUTED, ACCENT, FONT

# (anahtar, çubuktaki ad)
PANELS = [("target", "Hedef Pencere"), ("list", "Makro"), ("editor", "Aksiyon Editörü"),
          ("clicker", "Hızlı Tıklayıcı"), ("runner", "Makroyu Çalıştır"), ("status", "Durum Çubuğu")]


class ViewMixin:
    # ================= GÖRÜNÜM =================
    def _build_view_bar(self, parent):
        self.view_vars = {k: tk.BooleanVar(value=True) for k, _ in PANELS}
        self._view_chips = {}
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 2))
        self._muted(bar, "Görünüm", 11).pack(side="left", padx=(2, 10))
        for key, text in PANELS:
            b = ctk.CTkButton(bar, text=text, command=lambda k=key: self.toggle_panel(k), width=0, height=26,
                              corner_radius=13, border_width=1, font=ctk.CTkFont(FONT, 11, "bold"))
            b.pack(side="left", padx=(0, 6))
            self._view_chips[key] = (b, text)
        self._ghost_btn(bar, "Tümünü göster", self.show_all_panels, width=110).pack(side="right")

    def toggle_panel(self, key):
        var = self.view_vars[key]
        var.set(not var.get())
        self.apply_view()

    def show_all_panels(self):
        for var in self.view_vars.values():
            var.set(True)
        self.apply_view()

    def hidden_panels(self):
        return [k for k, var in self.view_vars.items() if not var.get()]

    def set_hidden_panels(self, keys):
        for k, var in self.view_vars.items():
            var.set(k not in keys)
        self.apply_view()

    def apply_view(self):
        v = {k: var.get() for k, var in self.view_vars.items()}
        p = self.panels

        for key, (b, text) in self._view_chips.items():
            if v[key]:
                b.configure(text=f"✓  {text}", fg_color="#1d2540", hover_color="#253055",
                            text_color=ACCENT, border_color="#2f3d6b")
            else:
                b.configure(text=text, fg_color=SURFACE2, hover_color=SURFACE3,
                            text_color=MUTED, border_color=BORDER)

        def show(w, on, **grid):
            if on:
                w.grid(**grid)
            else:
                w.grid_remove()

        show(p["target"], v["target"])
        show(p["status"], v["status"])

        # Orta: liste + editör. Tek panel kalınca boş alanı o doldurur.
        mid = p["mid"]
        show(mid, v["list"] or v["editor"])
        both = v["list"] and v["editor"]
        show(p["list"], v["list"], padx=(0, 14) if both else 0)
        show(p["editor"], v["editor"])
        mid.grid_columnconfigure(0, weight=1 if v["list"] else 0)
        mid.grid_columnconfigure(1, weight=0 if v["list"] else 1)
        self.root.grid_rowconfigure(3, weight=1 if (v["list"] or v["editor"]) else 0)

        # Alt: tıklayıcı + çalıştırıcı
        bottom = p["bottom"]
        show(bottom, v["clicker"] or v["runner"])
        pair = v["clicker"] and v["runner"]
        show(p["clicker"], v["clicker"], padx=(0, 7) if pair else 0)
        show(p["runner"], v["runner"], padx=(7, 0) if pair else 0)
        bottom.grid_columnconfigure(0, weight=2 if v["clicker"] else 0)
        bottom.grid_columnconfigure(1, weight=3 if v["runner"] else 0)

        # Panel gizlenince pencere daha küçük boyutlara indirilebilsin
        wide = both or pair
        self.root.minsize(1140 if wide else 760, 780 if (v["list"] or v["editor"]) else 0)

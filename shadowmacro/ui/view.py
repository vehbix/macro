"""Görünüm çubuğu: panelleri göster/gizle ve yerleşimi buna göre yeniden kur."""
import math
import tkinter as tk

import customtkinter as ctk

from .theme import SURFACE2, SURFACE3, BORDER, MUTED, ACCENT, AMBER, FONT

# (anahtar, çubuktaki ad)
PANELS = [("target", "Hedef Pencere"), ("list", "Makro"), ("editor", "Aksiyon Editörü"),
          ("clicker", "Hızlı Tıklayıcı"), ("runner", "Makroyu Çalıştır"), ("status", "Durum Çubuğu")]


class ViewMixin:
    # ================= GÖRÜNÜM =================
    def _build_view_bar(self, parent):
        self.view_vars = {k: tk.BooleanVar(value=True) for k, _ in PANELS}
        self.mini_mode = False
        self._full_geometry = None
        self._view_chips = {}
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 2))
        self.panels["viewbar"] = bar
        self._muted(bar, "Görünüm", 11).pack(side="left", padx=(2, 10))
        for key, text in PANELS:
            b = ctk.CTkButton(bar, text=text, command=lambda k=key: self.toggle_panel(k), width=0, height=26,
                              corner_radius=13, border_width=1, font=ctk.CTkFont(FONT, 11, "bold"))
            b.pack(side="left", padx=(0, 6))
            self._view_chips[key] = (b, text)
        self._ghost_btn(bar, "⤡  Mini", self.toggle_mini, width=74).pack(side="right")
        self._ghost_btn(bar, "Tümünü göster", self.show_all_panels, width=110).pack(side="right", padx=(0, 6))

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

    def toggle_mini(self):
        """Mini mod: sadece hızlı tıklayıcının tek satırlık kompakt hali kalır."""
        if not self.mini_mode:
            self._full_geometry = self.root.geometry()
        self.set_mini(not self.mini_mode)

    def set_mini(self, on):
        self.mini_mode = bool(on)
        self.apply_view()
        if not self.mini_mode:
            self.root.geometry(self._full_geometry or "1280x880")

    def toggle_pin(self):
        self.always_on_top.set(not self.always_on_top.get())
        self.toggle_always_on_top()
        self._update_pin_button()

    def _update_pin_button(self):
        if self.always_on_top.get():
            self._btn_mini_pin.configure(fg_color="#3a2f1a", border_color=AMBER)
        else:
            self._btn_mini_pin.configure(fg_color=SURFACE2, border_color=BORDER)

    def _apply_mini(self, on):
        """Tıklayıcı kartını kompakt/normal düzene geçirir."""
        if on:
            self._clk_head.grid_remove()
            self._clk_hint.grid_remove()
            self._clk_cps_lbl.grid_remove()
            self._clk_row.grid_configure(padx=8, pady=8)
            self.cps_slider.configure(width=110)
            self.btn_f7.configure(height=32, width=96)
            self._btn_mini_pin.grid(row=0, column=4, padx=(8, 0))
            self._btn_mini_exit.grid(row=0, column=5, padx=(6, 0))
            self._update_pin_button()
        else:
            self._clk_head.grid()
            self._clk_hint.grid()
            self._clk_cps_lbl.grid()
            self._clk_row.grid_configure(padx=18, pady=(10, 14))
            self.cps_slider.configure(width=200)
            self.btn_f7.configure(height=36, width=104)
            self._btn_mini_pin.grid_remove()
            self._btn_mini_exit.grid_remove()

    def apply_view(self):
        v = {k: var.get() for k, var in self.view_vars.items()}
        p = self.panels
        mini = self.mini_mode
        self._apply_mini(mini)
        if mini:
            # tıklayıcı dışında her şey gizlenir; görünüm seçimleri korunur
            v = {k: k == "clicker" for k in v}
        for key in ("header", "viewbar"):
            if mini:
                p[key].grid_remove()
            else:
                p[key].grid()

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
        show(bottom, v["clicker"] or v["runner"], padx=6 if mini else 20, pady=6)
        pair = v["clicker"] and v["runner"]
        show(p["clicker"], v["clicker"], padx=(0, 7) if pair else 0)
        show(p["runner"], v["runner"], padx=(7, 0) if pair else 0)
        bottom.grid_columnconfigure(0, weight=2 if v["clicker"] else 0)
        bottom.grid_columnconfigure(1, weight=3 if v["runner"] else 0)

        if mini:
            # pencereyi kompakt şeridin gerçek boyutuna küçült
            self.root.update_idletasks()
            scale = self.root._get_window_scaling()
            w = math.ceil(self.root.winfo_reqwidth() / scale)
            h = math.ceil(self.root.winfo_reqheight() / scale)
            self.root.minsize(w, h)
            self.root.geometry(f"{w}x{h}")
            return

        # Panel gizlenince pencere daha küçük boyutlara indirilebilsin
        wide = both or pair
        self.root.minsize(1140 if wide else 760, 780 if (v["list"] or v["editor"]) else 0)

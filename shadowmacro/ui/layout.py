"""Ana pencere yerleşimi: üst bar, görünüm çubuğu, hedef pencere, liste, editör, tıklayıcı, çalıştırıcı."""
from tkinter import ttk

import customtkinter as ctk

from ..actions import TYPES
from .theme import (SURFACE, SURFACE2, SURFACE3, BORDER, TEXT, MUTED, ACCENT, ACCENT_H,
                    GREEN, GREEN_H, RED, AMBER, AMBER_H, FONT)


class LayoutMixin:
    # ================= ARAYÜZ =================
    def create_gui(self):
        r = self.root
        r.grid_columnconfigure(0, weight=1)
        r.grid_rowconfigure(3, weight=1)
        self.panels = {}

        # ---------- ÜST BAR ----------
        header = ctk.CTkFrame(r, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 6))
        header.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text="◆", font=ctk.CTkFont(FONT, 24, "bold"), text_color=ACCENT).pack(side="left")
        ctk.CTkLabel(brand, text="ShadowMacro", font=ctk.CTkFont(FONT, 22, "bold"), text_color=TEXT).pack(side="left", padx=(8, 8))
        ctk.CTkLabel(brand, text="V12", font=ctk.CTkFont(FONT, 11, "bold"), text_color=ACCENT,
                     fg_color="#1d2540", corner_radius=6, width=36, height=22).pack(side="left", pady=(4, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e")
        self.status_pill = ctk.CTkLabel(right, text="", font=ctk.CTkFont(FONT, 12, "bold"),
                                        corner_radius=12, height=28, width=160)
        self.status_pill.pack(side="left", padx=(0, 16))
        self._switch(right, "Üstte tut", self.always_on_top, self.toggle_always_on_top).pack(side="left")

        # ---------- GÖRÜNÜM ÇUBUĞU ----------
        self._build_view_bar(r)

        # ---------- HEDEF PENCERE ----------
        target = self._card(r)
        target.grid(row=2, column=0, sticky="ew", padx=20, pady=6)
        self.panels["target"] = target
        target.grid_columnconfigure(1, weight=1)

        tleft = ctk.CTkFrame(target, fg_color="transparent")
        tleft.grid(row=0, column=0, sticky="w", padx=(18, 12), pady=12)
        self._title(tleft, "Hedef Pencere").pack(anchor="w")
        self.lbl_mode_hint = self._muted(tleft, "", 11)
        self.lbl_mode_hint.pack(anchor="w")

        self.cb_window = ctk.CTkComboBox(target, variable=self.target_window_title, values=[], state="readonly",
                                         height=36, corner_radius=8, fg_color=SURFACE2, border_color=BORDER,
                                         button_color=SURFACE3, button_hover_color=BORDER, text_color=TEXT,
                                         dropdown_fg_color=SURFACE2, dropdown_hover_color=SURFACE3,
                                         dropdown_text_color=TEXT, font=ctk.CTkFont(FONT, 12),
                                         command=lambda _: self.update_mode_hint())
        self.cb_window.grid(row=0, column=1, sticky="ew", pady=12)
        self._ghost_btn(target, "↻", self.refresh_windows, width=38).grid(row=0, column=2, padx=8)
        self._switch(target, "Pencere Modu", self.use_window_mode, self.update_mode_hint, GREEN).grid(
            row=0, column=3, padx=(8, 18))

        # ---------- ORTA: LİSTE + EDİTÖR ----------
        mid = ctk.CTkFrame(r, fg_color="transparent")
        mid.grid(row=3, column=0, sticky="nsew", padx=20, pady=6)
        self.panels["mid"] = mid
        mid.grid_columnconfigure(0, weight=1)
        mid.grid_rowconfigure(0, weight=1)

        self._build_list(mid)
        self._build_editor(mid)

        # ---------- ALT: TIKLAYICI + MAKRO ----------
        bottom = ctk.CTkFrame(r, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=20, pady=6)
        self.panels["bottom"] = bottom
        bottom.grid_columnconfigure(0, weight=2)
        bottom.grid_columnconfigure(1, weight=3)
        self._build_clicker(bottom)
        self._build_runner(bottom)

        # ---------- DURUM ÇUBUĞU ----------
        sbar = ctk.CTkFrame(r, fg_color=SURFACE, corner_radius=0, height=30)
        sbar.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        self.panels["status"] = sbar
        sbar.grid_columnconfigure(0, weight=1)
        self.lbl_status = ctk.CTkLabel(sbar, text="", font=ctk.CTkFont(FONT, 11), text_color=MUTED, anchor="w")
        self.lbl_status.grid(row=0, column=0, sticky="w", padx=16, pady=4)
        self.lbl_cursor = ctk.CTkLabel(sbar, text="", font=ctk.CTkFont("Consolas", 11), text_color=MUTED)
        self.lbl_cursor.grid(row=0, column=1, sticky="e", padx=16)

        # Kısayollar
        r.bind("<Control-s>", lambda e: self.save_project())
        r.bind("<Control-o>", lambda e: self.load_project())

        self.update_mode_hint()
        self.apply_view()
        self.on_type_change()
        self.set_status("Hazır. Aksiyon ekle ya da canlı kayıt başlat.")

    def _build_list(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.panels["list"] = card
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 0))
        head.grid_columnconfigure(1, weight=1)
        self._title(head, "Makro").grid(row=0, column=0, sticky="w")
        self.lbl_count = ctk.CTkLabel(head, text="0", font=ctk.CTkFont(FONT, 11, "bold"), text_color=MUTED,
                                      fg_color=SURFACE3, corner_radius=10, width=30, height=20)
        self.lbl_count.grid(row=0, column=1, sticky="w", padx=8)
        self.btn_rec = ctk.CTkButton(head, text="🔴  Canlı Kayıt", command=self.toggle_recording, width=130,
                                     height=32, corner_radius=8, fg_color="#3a2328", hover_color="#4a2a30",
                                     text_color=RED, font=ctk.CTkFont(FONT, 12, "bold"))
        self.btn_rec.grid(row=0, column=2, padx=(0, 12))
        self._ghost_btn(head, "📂  Aç", self.load_project, width=72).grid(row=0, column=3, padx=4)
        self._ghost_btn(head, "💾  Kaydet", self.save_project, width=92).grid(row=0, column=4)

        tabs = ctk.CTkTabview(card, fg_color=SURFACE, corner_radius=10, height=200,
                              segmented_button_fg_color=SURFACE2, segmented_button_selected_color=ACCENT,
                              segmented_button_selected_hover_color=ACCENT_H,
                              segmented_button_unselected_color=SURFACE2,
                              segmented_button_unselected_hover_color=SURFACE3, text_color=TEXT, anchor="w")
        tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 4))
        t_list = tabs.add("Aksiyonlar")
        t_log = tabs.add("Günlük")
        self.tabs = tabs

        # --- Aksiyon listesi ---
        t_list.grid_columnconfigure(0, weight=1)
        t_list.grid_rowconfigure(0, weight=1)
        holder = ctk.CTkFrame(t_list, fg_color=SURFACE2, corner_radius=10)
        holder.grid(row=0, column=0, sticky="nsew")
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)

        cols = ("ID", "On", "Type", "Detail", "Delay")
        self.tree = ttk.Treeview(holder, columns=cols, show="headings", selectmode="browse", style="Macro.Treeview")
        self.tree.heading("ID", text="#"); self.tree.column("ID", width=40, anchor="center", stretch=False)
        self.tree.heading("On", text=""); self.tree.column("On", width=26, anchor="center", stretch=False)
        self.tree.heading("Type", text="İşlem", anchor="w"); self.tree.column("Type", width=150, stretch=False)
        self.tree.heading("Detail", text="Detay", anchor="w"); self.tree.column("Detail", width=280)
        self.tree.heading("Delay", text="Bekleme"); self.tree.column("Delay", width=84, anchor="center", stretch=False)
        self.tree.tag_configure("odd", background="#1b1f27")
        self.tree.tag_configure("label", foreground=ACCENT, font=(FONT, 10, "bold"))
        self.tree.tag_configure("flow", foreground="#b9a6ff")
        self.tree.tag_configure("disabled", foreground="#5b6272")
        self.tree.tag_configure("running", background="#4a3b17", foreground="#ffe1a6")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sb = ctk.CTkScrollbar(holder, command=self.tree.yview, fg_color="transparent",
                              button_color=SURFACE3, button_hover_color=BORDER)
        sb.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Delete>", lambda e: self.delete_row())
        self.tree.bind("<space>", lambda e: self.toggle_enabled())
        self.tree.bind("<Escape>", lambda e: self.clear_selection())

        self.lbl_empty = ctk.CTkLabel(holder, text="Henüz aksiyon yok\n\nSağdaki panelden ekle ya da\nCanlı Kayıt ile tıklama ve tuşlarını kaydet",
                                      font=ctk.CTkFont(FONT, 13), text_color=MUTED, fg_color=SURFACE2)

        bar = ctk.CTkFrame(t_list, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(10, 2))
        self._ghost_btn(bar, "▲", lambda: self.move_row(-1)).pack(side="left", padx=(0, 4))
        self._ghost_btn(bar, "▼", lambda: self.move_row(1)).pack(side="left", padx=(0, 4))
        self._ghost_btn(bar, "⧉  Çoğalt", self.duplicate_row, width=86).pack(side="left", padx=(8, 4))
        self._ghost_btn(bar, "⏻  Aç/Kapat", self.toggle_enabled, width=96).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Sil", command=self.delete_row, width=60, height=32, corner_radius=8,
                      fg_color="#3a2328", hover_color="#4a2a30", text_color=RED,
                      font=ctk.CTkFont(FONT, 12, "bold")).pack(side="left", padx=4)
        self._ghost_btn(bar, "Tümünü Temizle", self.clear_all, width=120).pack(side="right")

        # --- Günlük ---
        t_log.grid_columnconfigure(0, weight=1)
        t_log.grid_rowconfigure(0, weight=1)
        self.log_box = ctk.CTkTextbox(t_log, fg_color=SURFACE2, text_color=TEXT, corner_radius=10,
                                      font=ctk.CTkFont("Consolas", 11), wrap="word")
        self.log_box.grid(row=0, column=0, sticky="nsew")
        self.log_box.configure(state="disabled")
        lbar = ctk.CTkFrame(t_log, fg_color="transparent")
        lbar.grid(row=1, column=0, sticky="ew", pady=(10, 2))
        self._ghost_btn(lbar, "Günlüğü Temizle", self.clear_log, width=130).pack(side="right")
        self._muted(lbar, "Koşullar, atlamalar, bildirimler ve hatalar burada görünür.", 11).pack(side="left")

    def _build_editor(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=1, sticky="nsew")
        self.panels["editor"] = card
        card.configure(width=390)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 8))
        top.grid_columnconfigure(0, weight=1)
        self.lbl_editor_title = self._title(top, "Yeni Aksiyon")
        self.lbl_editor_title.grid(row=0, column=0, sticky="w")
        self._ghost_btn(top, "＋ Yeni", self.clear_selection, width=70).grid(row=0, column=1)

        self.opt_type = self._option(card, self.type_var, [l for _, l in TYPES], cmd=lambda _: self.on_type_change())
        self.opt_type.configure(height=36, font=ctk.CTkFont(FONT, 13, "bold"))
        self.opt_type.grid(row=1, column=0, sticky="ew", padx=18)

        self.form = ctk.CTkScrollableFrame(card, fg_color="transparent", scrollbar_button_color=SURFACE3,
                                           scrollbar_button_hover_color=BORDER)
        self.form.grid(row=2, column=0, sticky="nsew", padx=(10, 4), pady=(8, 0))
        self.form.grid_columnconfigure(0, weight=1)

        dl = ctk.CTkFrame(card, fg_color="transparent")
        dl.grid(row=3, column=0, sticky="ew", padx=18, pady=(6, 0))
        dl.grid_columnconfigure(0, weight=1)
        self.lbl_delay = self._muted(dl, "")
        self.lbl_delay.grid(row=0, column=0, sticky="w")
        self.ent_delay = self._entry(dl, self.delay_var)
        self.ent_delay.grid(row=1, column=0, sticky="ew")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", padx=18, pady=(12, 0))
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text="＋  Ekle", command=self.add_action, height=40, corner_radius=10,
                      fg_color=GREEN, hover_color=GREEN_H, text_color="#0b1a13",
                      font=ctk.CTkFont(FONT, 13, "bold")).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_update = ctk.CTkButton(btns, text="✓  Güncelle", command=self.update_action, height=40,
                                        corner_radius=10, fg_color=SURFACE2, hover_color=SURFACE3,
                                        text_color=TEXT, border_width=1, border_color=BORDER,
                                        font=ctk.CTkFont(FONT, 13, "bold"), state="disabled")
        self.btn_update.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.lbl_editor_hint = self._muted(card, "", 11)
        self.lbl_editor_hint.configure(wraplength=340)
        self.lbl_editor_hint.grid(row=5, column=0, sticky="w", padx=18, pady=(6, 12))

    def _build_clicker(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.panels["clicker"] = card
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 2))
        self._title(head, "Hızlı Tıklayıcı").pack(side="left")
        self._badge(head, "F7").pack(side="left", padx=8)
        self.lbl_f7_status = ctk.CTkLabel(head, text="● Durdu", font=ctk.CTkFont(FONT, 12, "bold"), text_color=MUTED)
        self.lbl_f7_status.pack(side="right")
        self._muted(card, "Pencere modunda editördeki X/Y noktasına sinyal gönderir.", 11).grid(
            row=1, column=0, sticky="w", padx=18)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=18, pady=(10, 14))
        row.grid_columnconfigure(1, weight=1)
        self._muted(row, "CPS").grid(row=0, column=0, padx=(0, 10))
        self.cps_slider = ctk.CTkSlider(row, from_=0, to=1, command=self.on_cps_slide, height=18,
                                        progress_color=AMBER, button_color=AMBER, button_hover_color=AMBER_H,
                                        fg_color=SURFACE3)
        self.cps_slider.grid(row=0, column=1, sticky="ew")
        ent = self._entry(row, self.cps_text, width=60)
        ent.configure(justify="center")
        ent.grid(row=0, column=2, padx=10)
        ent.bind("<Return>", lambda e: self.on_cps_entry())
        ent.bind("<FocusOut>", lambda e: self.on_cps_entry())
        self.btn_f7 = ctk.CTkButton(row, text="▶  Başlat", command=self.toggle_f7_clicker, width=104, height=36,
                                    corner_radius=10, fg_color=AMBER, hover_color=AMBER_H, text_color="#1f1606",
                                    font=ctk.CTkFont(FONT, 13, "bold"))
        self.btn_f7.grid(row=0, column=3)

    def _build_runner(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.panels["runner"] = card
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 2))
        self._title(head, "Makroyu Çalıştır").pack(side="left")
        self._badge(head, "F6").pack(side="left", padx=(8, 4))
        self._muted(head, "başlat/durdur", 11).pack(side="left")
        self._badge(head, "F8").pack(side="left", padx=(10, 4))
        self._muted(head, "duraklat", 11).pack(side="left")

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 0))
        for lbl, var in [("Tekrar · 0 = sonsuz", self.loop_var),
                         ("Süre sınırı (dk) · 0 = yok", self.limit_var),
                         ("Geri sayım (sn)", self.start_delay_var)]:
            box = ctk.CTkFrame(opts, fg_color="transparent")
            box.pack(side="left", padx=(0, 14))
            self._muted(box, lbl, 11).pack(anchor="w")
            self._entry(box, var, width=110).pack(anchor="w")
        sw = ctk.CTkFrame(opts, fg_color="transparent")
        sw.pack(side="left", padx=(4, 0))
        self._switch(sw, "Turbo", self.use_turbo_mode).pack(anchor="w", pady=(0, 4))
        self._switch(sw, "İnsansı", self.human_speed).pack(anchor="w")

        brow = ctk.CTkFrame(card, fg_color="transparent")
        brow.grid(row=2, column=0, sticky="ew", padx=18, pady=(10, 14))
        brow.grid_columnconfigure(0, weight=1)
        self.btn_play = ctk.CTkButton(brow, text="", command=self.toggle_macro, height=44, corner_radius=10,
                                      font=ctk.CTkFont(FONT, 14, "bold"))
        self.btn_play.grid(row=0, column=0, sticky="ew")
        self.btn_pause = ctk.CTkButton(brow, text="❚❚  Duraklat", command=self.toggle_pause, width=130, height=44,
                                       corner_radius=10, fg_color=SURFACE2, hover_color=SURFACE3, text_color=TEXT,
                                       border_width=1, border_color=BORDER, font=ctk.CTkFont(FONT, 13, "bold"),
                                       state="disabled")
        self.btn_pause.grid(row=0, column=1, padx=(8, 0))
        self._set_play_button(False)

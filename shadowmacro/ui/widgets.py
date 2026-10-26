"""ttk stilleri ve temalı widget kısayolları."""
from tkinter import ttk

import customtkinter as ctk

from .theme import SURFACE, SURFACE2, SURFACE3, BORDER, TEXT, MUTED, ACCENT, FONT


class WidgetsMixin:
    # ================= STİL =================
    def setup_styles(self):
        scale = self.root.winfo_fpixels("1i") / 96
        style = ttk.Style()
        style.theme_use("clam")
        style.layout("Macro.Treeview", [("Macro.Treeview.treearea", {"sticky": "nswe"})])
        style.configure("Macro.Treeview",
                        background=SURFACE2, foreground=TEXT, fieldbackground=SURFACE2,
                        font=(FONT, 10), rowheight=int(32 * scale), borderwidth=0, relief="flat")
        style.map("Macro.Treeview",
                  background=[("selected", ACCENT)], foreground=[("selected", "white")])
        style.configure("Macro.Treeview.Heading",
                        background=SURFACE, foreground=MUTED, font=(FONT, 9, "bold"),
                        relief="flat", borderwidth=0, padding=(8, 6))
        style.map("Macro.Treeview.Heading", background=[("active", SURFACE)])

    # ================= YARDIMCI WIDGET'LAR =================
    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=14, border_width=1, border_color=BORDER)

    def _title(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(FONT, 15, "bold"), text_color=TEXT)

    def _muted(self, parent, text, size=12):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(FONT, size), text_color=MUTED, justify="left")

    def _badge(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(FONT, 11, "bold"), text_color=TEXT,
                            fg_color=SURFACE3, corner_radius=6, width=34, height=22)

    def _entry(self, parent, var, width=None, placeholder=None):
        kw = {"width": width} if width else {}
        return ctk.CTkEntry(parent, textvariable=var, fg_color=SURFACE2, border_color=BORDER,
                            text_color=TEXT, corner_radius=8, height=32,
                            placeholder_text=placeholder, **kw)

    def _ghost_btn(self, parent, text, cmd, width=36):
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=32, corner_radius=8,
                             fg_color=SURFACE2, hover_color=SURFACE3, text_color=TEXT,
                             border_width=1, border_color=BORDER, font=ctk.CTkFont(FONT, 12))

    def _switch(self, parent, text, var, cmd=None, color=ACCENT):
        return ctk.CTkSwitch(parent, text=text, variable=var, command=cmd, onvalue=True, offvalue=False,
                             progress_color=color, button_color="#ffffff", button_hover_color="#dfe3ea",
                             fg_color=SURFACE3, text_color=TEXT, font=ctk.CTkFont(FONT, 12))

    def _option(self, parent, var, values, cmd=None, width=None):
        kw = {"width": width} if width else {}
        return ctk.CTkOptionMenu(parent, variable=var, values=values, command=cmd, height=32, corner_radius=8,
                                 fg_color=SURFACE2, button_color=SURFACE3, button_hover_color=BORDER,
                                 text_color=TEXT, dropdown_fg_color=SURFACE2, dropdown_hover_color=SURFACE3,
                                 dropdown_text_color=TEXT, font=ctk.CTkFont(FONT, 12),
                                 dropdown_font=ctk.CTkFont(FONT, 12), dynamic_resizing=False, **kw)

"""Renkler, yazı tipi ve CPS kaydırıcı ölçeği."""
import math

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#0f1115"
SURFACE = "#171a21"
SURFACE2 = "#1f232c"
SURFACE3 = "#282d38"
BORDER = "#2c313c"
TEXT = "#e6e8ee"
MUTED = "#8b93a5"
ACCENT = "#6c8cff"
ACCENT_H = "#5a78e6"
GREEN = "#34c38f"
GREEN_H = "#2aa87a"
RED = "#f46a6a"
RED_H = "#d95757"
AMBER = "#f1b44c"
AMBER_H = "#d99d3a"

FONT = "Segoe UI"


def _cps_to_slider(cps):
    # Logaritmik ölçek: 1-1000 aralığında düşük hızlar da rahat ayarlanır
    return math.log10(max(1.0, min(1000.0, cps))) / 3


def _slider_to_cps(v):
    return max(1, min(1000, round(10 ** (3 * v))))

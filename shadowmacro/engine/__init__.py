"""Çalışma motoru: makro yürütücü, hızlı tıklayıcı ve canlı kayıt (mixin)."""
import pyautogui

# --- GÜVENLİK ---
# Fare ekranın bir köşesine götürülürse gerçek girişli makro/tıklayıcı durur.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

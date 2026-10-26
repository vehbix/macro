"""ShadowMacro — Windows için makro kaydedici ve hızlı tıklayıcı."""
import sys

if sys.platform != "win32":
    raise SystemExit("ShadowMacro V12 sadece Windows'ta çalışır.")

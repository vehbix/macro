from shadowmacro.deps import ensure_requirements

# Eksik paketler, onları kullanan modüller içe aktarılmadan önce kurulmalı
ensure_requirements()

import customtkinter as ctk  # noqa: E402

from shadowmacro.app import ShadowMacroV12  # noqa: E402


if __name__ == "__main__":
    root = ctk.CTk()
    app = ShadowMacroV12(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

"""Uygulama ayarlarının config.json'a kaydedilip yüklenmesi."""
import json
import os

# config.json depo kökünde (macro.py'nin yanında) durur
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


class ConfigMixin:
    def load_config(self):
        d = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as f: d = json.load(f)
            except Exception:
                d = {}
        self.set_cps(d.get("f7", 10))
        self.use_turbo_mode.set(d.get("turbo", False))
        self.human_speed.set(d.get("human", True))
        self.loop_var.set(str(d.get("loops", 0)))
        self.limit_var.set(f"{d.get('limit', 0):g}")
        self.start_delay_var.set(f"{d.get('start_delay', 0):g}")
        self.use_window_mode.set(d.get("window_mode", False))
        self.target_window_title.set(d.get("target", ""))
        self.always_on_top.set(d.get("top", False))
        self.set_hidden_panels(d.get("hidden", []))
        if d.get("mini"):
            self.toggle_mini()
        self.toggle_always_on_top()
        self.update_mode_hint()

    def save_config(self):
        def num(var, cast):
            try:
                return max(0, cast(str(var.get()).replace(",", ".") or 0))
            except ValueError:
                return 0
        d = {"f7": self.f7_cps, "turbo": self.use_turbo_mode.get(), "human": self.human_speed.get(),
             "loops": num(self.loop_var, int), "limit": num(self.limit_var, float),
             "start_delay": num(self.start_delay_var, float), "top": self.always_on_top.get(),
             "window_mode": self.use_window_mode.get(), "target": self.target_window_title.get(),
             "hidden": self.hidden_panels(), "mini": self.mini_mode}
        try:
            with open(CONFIG_PATH, "w") as f: json.dump(d, f)
        except Exception:
            pass

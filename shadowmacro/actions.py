"""Aksiyon tanımları: tipler, editör şeması ve eski dosya uyumluluğu."""


TYPES = [
    ("Click", "🖱  Tıkla"), ("Move", "➜  Fare Taşı"), ("Drag", "✋  Sürükle"),
    ("Press", "⌨  Tuş"), ("Type", "✎  Yazı Yaz"), ("Scroll", "↕  Kaydır"), ("Wait", "⏱  Bekle"),
    ("WaitColor", "🎨  Renk Bekle"), ("IfColor", "❔  Renk Kontrol"),
    ("FindImage", "🔍  Resim Bul"), ("FindColor", "🎯  Renk Ara"),
    ("Label", "🏷  Etiket"), ("Goto", "↩  Git"), ("Notify", "🔔  Bildirim"),
]
TYPE_LABELS = dict(TYPES)
TYPE_FROM_LABEL = {v: k for k, v in TYPES}

BTN = [("left", "Sol"), ("right", "Sağ"), ("middle", "Orta")]
KEYMODE = [("tap", "Bas ve bırak"), ("down", "Basılı tut (bırakma)"), ("up", "Bırak")]
UNTIL = [("appear", "Görünene kadar"), ("vanish", "Kaybolana kadar")]
FOUNDCLICK = [("left", "Sol tıkla"), ("right", "Sağ tıkla"), ("double", "Çift tıkla"),
              ("move", "Sadece imleci götür"), ("none", "Hiçbir şey yapma")]

# (anahtar, etiket, tür, seçenekler/ipucu, varsayılan)
SCHEMA = {
    "Click": [("button", "Fare tuşu", "choice", BTN, "left"),
              ("double", "Çift tıklama", "bool", None, False),
              ("hold", "Basılı tutma süresi (sn) · 0 = normal tık", "float", None, 0.0),
              ("here", "Konum yerine imlecin olduğu yere tıkla", "bool", None, False),
              ("xy", "Konum", "xy", None, None)],
    "Move": [("xy", "Hedef konum (göreli modda: kaydırma miktarı)", "xy", None, None),
             ("relative", "Göreli hareket (FPS oyun kamerası için)", "bool", None, False)],
    "Drag": [("xy", "Başlangıç", "xy", None, None),
             ("xy2", "Bitiş", "xy", None, None),
             ("button", "Fare tuşu", "choice", BTN, "left"),
             ("duration", "Sürükleme süresi (sn)", "float", None, 0.3)],
    "Press": [("key", "Tuş veya kombinasyon", "text", "a, enter, f5, ctrl+c, shift+tab", "enter"),
              ("mode", "Davranış", "choice", KEYMODE, "tap"),
              ("hold", "Basılı tutma süresi (sn) · 'Bas ve bırak' için", "float", None, 0.0)],
    "Type": [("text", "Yazılacak metin (\\n = Enter)", "text", "Merhaba!", ""),
             ("interval", "Harfler arası bekleme (sn)", "float", None, 0.02)],
    "Scroll": [("amount", "Miktar · bir çentik = 120 (yukarı +, aşağı −)", "int", None, -120)],
    "Wait": [],
    "WaitColor": [("color", "Renk (R,G,B)", "color", None, ""),
                  ("xy", "Konum", "xy", None, None),
                  ("tolerance", "Tolerans (0-255)", "int", None, 10),
                  ("until", "Bekleme koşulu", "choice", UNTIL, "appear"),
                  ("timeout", "Zaman aşımı (sn)", "float", None, 5.0),
                  ("on_timeout", "Zaman aşılırsa", "outcome", None, "next")],
    "IfColor": [("color", "Renk (R,G,B)", "color", None, ""),
                ("xy", "Konum", "xy", None, None),
                ("tolerance", "Tolerans (0-255)", "int", None, 10),
                ("on_true", "Renk eşleşirse", "outcome", None, "next"),
                ("on_false", "Eşleşmezse", "outcome", None, "next")],
    "FindImage": [("image", "Aranacak resim", "image", None, ""),
                  ("confidence", "Benzerlik eşiği (0.5 - 1.0)", "float", None, 0.85),
                  ("timeout", "Arama süresi (sn) · 0 = tek bakış", "float", None, 0.0),
                  ("click", "Bulununca", "choice", FOUNDCLICK, "left"),
                  ("on_found", "Bulunursa sonra", "outcome", None, "next"),
                  ("on_missing", "Bulunamazsa", "outcome", None, "next")],
    "FindColor": [("color", "Aranacak renk (R,G,B)", "color", None, ""),
                  ("tolerance", "Tolerans (0-255)", "int", None, 10),
                  ("timeout", "Arama süresi (sn) · 0 = tek bakış", "float", None, 0.0),
                  ("click", "Bulununca", "choice", FOUNDCLICK, "left"),
                  ("on_found", "Bulunursa sonra", "outcome", None, "next"),
                  ("on_missing", "Bulunamazsa", "outcome", None, "next")],
    "Label": [("name", "Etiket adı", "text", "örn. başla", "")],
    "Goto": [("label", "Gidilecek etiket", "labelref", None, ""),
             ("times", "Kaç kez gidilsin (0 = her zaman)", "int", None, 0)],
    "Notify": [("text", "Mesaj", "text", "örn. Envanter doldu", ""),
               ("beep", "Sesli uyarı", "bool", None, True),
               ("stop", "Makroyu durdur", "bool", None, False)],
}
XY_KEYS = {"xy": ("x", "y"), "xy2": ("x2", "y2")}


def _choice_label(choices, value):
    return dict(choices).get(value, choices[0][1])


def _choice_value(choices, label):
    for v, l in choices:
        if l == label:
            return v
    return choices[0][0]


def _outcome_text(v):
    if v == "stop": return "dur"
    if isinstance(v, str) and v.startswith("goto:"): return "→ " + v[5:]
    return "devam"


def _normalize(a):
    """Eski sürüm (V8-V11) dosyalarını da okuyabilmek için eksik alanları tamamlar."""
    a = dict(a)
    t = a.get("type")
    if t not in SCHEMA:
        return None
    a.setdefault("enabled", True)
    a.setdefault("delay", 0)
    if t == "WaitColor" and "timeout" not in a:
        # V8-V11'de WaitColor'ın "delay" alanı zaman aşımıydı
        a["timeout"] = float(a.get("delay") or 5)
        a["delay"] = 0
    for key, _l, kind, _o, default in SCHEMA[t]:
        if kind == "xy":
            for k in XY_KEYS[key]:
                a.setdefault(k, 0)
        else:
            a.setdefault(key, default)
    return a


class _Stop(Exception):
    pass

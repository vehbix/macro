"""İsteğe bağlı opencv/numpy bağımlılığı (Resim Bul ve Renk Ara için)."""
try:
    import numpy as np
    import cv2
    HAS_CV = True
except ImportError:
    np = None
    cv2 = None
    HAS_CV = False

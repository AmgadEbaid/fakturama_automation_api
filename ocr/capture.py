"""OCR capture: screenshot a pane + run native Windows OCR. No formatting here."""
from PIL import ImageGrab, ImageEnhance
import winocr


def capture_raw(pane):
    """Returns (raw_ocr_dict, table_rect). Coords in raw are image pixels from pane top-left."""
    r = pane.BoundingRectangle
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    raw = winocr.recognize_pil_sync(img, lang="en")
    return raw, r


def capture_preprocessed(pane, scale=2):
    """Upscaled + contrast boosted capture for inverted/highlighted canvas rows.

    Returns (raw_ocr_dict, table_rect, scale). Raw coords are scale x screen px.
    """
    r = pane.BoundingRectangle
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    w, h = img.size
    img = img.resize((w * scale, h * scale), resample=2)
    img = ImageEnhance.Contrast(img.convert("L")).enhance(2.5)
    raw = winocr.recognize_pil_sync(img, lang="en")
    return raw, r, scale

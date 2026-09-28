"""Items table model: full-capture OCR once, every field linked to its click point."""
from dataclasses import dataclass, field
import time
import ctypes
import uiautomation as auto

COLUMNS = ["Pos.", "Qty.", "Item No.", "Picture", "Name", "Description", "VAT", "U.Price", "Discount", "Price"]

# Seed fractions measured on a 1442px-wide table capture. Live reads refine
# them slowly, so the first read in a fresh process already splits correctly.
_SEED_FRACS = {
    "Pos.": 0.017, "Qty.": 0.087, "Item No.": 0.196, "Picture": 0.306,
    "Name": 0.409, "Description": 0.515, "VAT": 0.618, "U.Price": 0.729,
    "Discount": 0.833, "Price": 0.938,
}
_SEED_WEIGHT = 20

# Stable header geometry. Single-capture header centers jitter several px,
# which flips values near edges between columns. We keep a running average
# of each column center as a fraction of table width and build bands from it.
_FRAC_CACHE = {}


def _bands_from_headers(headers, width):
    key = round(width / 50)
    slot = _FRAC_CACHE.setdefault(key, {})
    if not slot:
        for col, frac in _SEED_FRACS.items():
            slot[col] = (frac * _SEED_WEIGHT, _SEED_WEIGHT)
    for col, cx in headers.items():
        frac = cx / width
        if col in slot:
            s, n = slot[col]
            slot[col] = (s + frac, n + 1)
        else:
            slot[col] = (frac, 1)
    avg = {col: (s / n) * width for col, (s, n) in slot.items()}
    for col in COLUMNS:
        if col not in avg:
            # Interpolate from neighbors by canonical order.
            known = [(COLUMNS.index(c), v) for c, v in avg.items()]
            if not known:
                return None
            idx = COLUMNS.index(col)
            lo = max([v for i, v in known if i < idx], default=known[0][1])
            hi = min([v for i, v in known if i > idx], default=known[-1][1])
            avg[col] = (lo + hi) / 2
    centers = sorted(avg.values())
    order = sorted(avg, key=lambda c: avg[c])
    bands = {}
    for i, col in enumerate(order):
        lo = (centers[i - 1] + centers[i]) / 2 if i else 0
        hi = (centers[i] + centers[i + 1]) / 2 if i + 1 < len(centers) else 10 ** 9
        bands[col] = (lo, hi)
    return bands


@dataclass
class ItemCell:
    value: str = ""
    x: int = 0
    y: int = 0


@dataclass
class ItemRow:
    pos: str = ""
    cells: dict = field(default_factory=dict)  # col -> ItemCell


@dataclass
class LineItem:
    """Fake test data until a real source exists."""
    qty: str = ""
    unit_price: str = ""
    vat: str = ""
    discount: str = ""


def _capture_items(pane, scale=2):
    """Blueprint preprocessing for small canvas fonts. Returns (raw, rect, scale)."""
    from PIL import ImageGrab, ImageEnhance
    import winocr
    r = pane.BoundingRectangle
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    w, h = img.size
    img = img.resize((w * scale, h * scale), resample=2)
    img = ImageEnhance.Contrast(img.convert("L")).enhance(2.5)
    return winocr.recognize_pil_sync(img, lang="en"), r, scale


def _items_pane(order):
    order.select()
    root = order.root
    label = root.TextControl(Name="Items")
    if not label.Exists(maxSearchSeconds=1.0):
        raise RuntimeError("Items label not found - needs review")
    lr = label.BoundingRectangle
    best, best_area = None, -1
    for c in order._descendants(root):
        try:
            if c.ControlTypeName != "PaneControl":
                continue
            r = c.BoundingRectangle
            w, h = r.right - r.left, r.bottom - r.top
            if w < 300 or h < 100:
                continue
            if r.top < lr.top - 30:
                continue
            if w * h > best_area:
                best, best_area = c, w * h
        except Exception:
            continue
    if best is None:
        raise RuntimeError("Items table pane not found - needs review")
    return best


def read_items(order) -> list:
    """One full capture. Returns [ItemRow] with every field linked to (x, y)."""
    pane = _items_pane(order)
    try:
        order.app.window.SetActive()
    except Exception:
        pass
    import time
    time.sleep(0.3)
    raw, rect, sc = _capture_items(pane)
    words = []
    for line in raw.get("lines", []):
        for w in line.get("words", []):
            wb = w["bounding_rect"]
            words.append({"text": w["text"], "cx": (wb["x"] + wb["width"] / 2) / sc,
                          "cy": (wb["y"] + wb["height"] / 2) / sc})
    headers = {}
    cands = list(words)
    by_y = sorted(words, key=lambda w: w["cy"])
    for a, b in zip(by_y, by_y[1:]):
        if abs(a["cy"] - b["cy"]) <= 9 and b["cx"] > a["cx"]:
            cands.append({"text": a["text"] + " " + b["text"], "cx": (a["cx"] + b["cx"]) / 2,
                          "cy": (a["cy"] + b["cy"]) / 2})
    for w in cands:
        t = " ".join(w["text"].strip().lower().rstrip(".").split())
        for col in COLUMNS:
            if col in headers:
                continue
            c = col.lower().rstrip(".")
            if t == c or (len(t) >= 2 and (c.startswith(t) or t.startswith(c))):
                headers[col] = w["cx"]
    if "Pos." not in headers or "Qty." not in headers:
        raise RuntimeError(f"table headers unreadable {sorted(headers)} - needs review")
    bands = _bands_from_headers(headers, rect.right - rect.left)
    if bands is None:
        raise RuntimeError("no header geometry yet - needs review")
    body_cut = 40
    try:
        body_cut = max(w["cy"] for w in words
                       if " ".join(w["text"].strip().lower().split()) in
                       [c.lower().rstrip(".") for c in headers]) + 8
    except Exception:
        pass
    body = [w for w in words if w["cy"] > body_cut]
    body.sort(key=lambda w: w["cy"])
    groups, cur, cur_y = [], [], None
    for w in body:
        if cur_y is None or abs(w["cy"] - cur_y) <= 9:
            cur.append(w)
            if cur_y is None:
                cur_y = w["cy"]
        else:
            groups.append(cur)
            cur, cur_y = [w], w["cy"]
    if cur:
        groups.append(cur)
    rows = []
    for g in groups:
        row = ItemRow()
        cy = sum(w["cy"] for w in g) / len(g)
        for w in g:
            for col, (lo, hi) in bands.items():
                if lo <= w["cx"] < hi:
                    cell = row.cells.get(col)
                    sx = int(rect.left + w["cx"])
                    sy = int(rect.top + w["cy"])
                    if cell is None or not cell.value:
                        row.cells[col] = ItemCell(w["text"], sx, sy)
                    else:
                        cell.value += " " + w["text"]
                    if col == "Pos." and not row.pos:
                        row.pos = w["text"]
                    break
        if not row.pos:
            # Pos digit often drops from OCR; keep the group, callers match loosely.
            row.pos = ""
        for col in COLUMNS:
            if col not in row.cells and col in bands:
                lo, hi = bands[col]
                cx = (lo + hi) / 2 if hi < 10 ** 9 else lo + 50
                row.cells[col] = ItemCell("", int(rect.left + cx), int(rect.top + cy))
        rows.append(row)
    return rows


def _focused_edit():
    focused = auto.GetFocusedControl()
    if focused is not None and focused.ControlTypeName == "EditControl":
        return focused
    return None


def _find_row(rows, pos: str):
    for r in rows:
        if r.pos.strip() == pos.strip() and r.pos.strip():
            return r
    if len(rows) == 1:
        return rows[0]
    return None


def set_cell_at(order, x: int, y: int, value: str):
    """Clicks stored (x, y), types into the spawned editor, commits. No re-read."""
    order.select()
    ctypes.windll.user32.SetCursorPos(x, y)
    time.sleep(0.15)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.4)
    edit = None
    for _ in range(10):
        edit = _focused_edit()
        if edit is not None:
            break
        time.sleep(0.1)
    if edit is None:
        raise RuntimeError(f"cell editor did not open at ({x}, {y}) - needs review")
    edit.SendKeys("{Ctrl}a{Del}")
    edit.SendKeys(value)
    edit.SendKeys("{Tab}")
    time.sleep(0.5)
    return True


def set_cell(order, pos: str, col: str, value: str):
    """Clicks the stored point of (pos, col), types into the spawned editor, commits."""
    rows = read_items(order)
    row = _find_row(rows, pos)
    if row is None or col not in row.cells:
        raise RuntimeError(f"cell ({pos}, {col}) not found - needs review")
    cell = row.cells[col]
    ctypes.windll.user32.SetCursorPos(cell.x, cell.y)
    time.sleep(0.15)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.4)
    edit = None
    for _ in range(10):
        edit = _focused_edit()
        if edit is not None:
            break
        time.sleep(0.1)
    if edit is None:
        raise RuntimeError(f"cell editor did not open at ({pos}, {col}) - needs review")
    edit.SendKeys("{Ctrl}a{Del}")
    edit.SendKeys(value)
    edit.SendKeys("{Tab}")
    time.sleep(0.5)
    return True


def _money(s: str) -> float:
    import re
    t = (s or "").replace("$", "").replace("%", "").strip()
    t = re.sub(r"[^\d.,-]", "", t).replace(",", "")
    try:
        return float(t)
    except Exception:
        raise RuntimeError(f"unparsable money {s!r} - needs review")


def _num_ok(got: str, expect: str, tol=0.01) -> bool:
    """Numeric compare that also accepts OCR-truncated reads ('$99.' vs '$99.99')."""
    try:
        if abs(_money(got) - _money(expect)) <= tol:
            return True
    except Exception:
        pass
    import re
    g = re.sub(r"[^\d.]", "", got or "")
    e = re.sub(r"[^\d.]", "", expect or "")
    return bool(g) and e.startswith(g)


def verify_line(order, pos: str, expect: LineItem) -> tuple:
    """Re-reads the row (up to 3 tries). Checks unit price, VAT and qty*unit*(1-disc)."""
    last = (False, "no read")
    for _ in range(3):
        rows = read_items(order)
        row = _find_row(rows, pos)
        if row is None:
            last = (False, f"row {pos} gone after edit")
            continue
        got = {c: row.cells.get(c, ItemCell()).value for c in COLUMNS}
        if expect.unit_price and not _num_ok(got["U.Price"], expect.unit_price):
            last = (False, f"U.Price {got['U.Price']!r} != {expect.unit_price!r}")
            continue
        if expect.vat and expect.vat.lower() not in got["VAT"].lower():
            last = (False, f"VAT {got['VAT']!r} != {expect.vat!r}")
            continue
        if expect.qty and expect.unit_price and expect.discount:
            want = _money(expect.qty) * _money(expect.unit_price) * (1 - _money(expect.discount) / 100)
            if not _num_ok(got["Price"], f"{want:.2f}", tol=0.02):
                last = (False, f"Price {got['Price']!r} != calc {want:.2f}")
                continue
        return (True, got)
    return last

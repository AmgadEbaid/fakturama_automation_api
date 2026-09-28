"""OCR format: raw winocr dict -> structured debtor-table rows. No screen capture here."""
from .capture import capture_raw

COL_NAMES = ["No.", "First Name", "Name", "Company", "ZIP", "City"]
# Calibrated on the 599px-wide reference capture; scaled live by table width.
BASE_ZONES = [(0, 95), (96, 190), (191, 280), (281, 380), (381, 480), (481, 10 ** 9)]
BASE_WIDTH = 599.0


def reconstruct_table(raw, table_rect, img_height):
    """Group words into rows (Y-cluster +-10px), skip header/chrome, map X into columns.

    Returns [{col: text, _x: screen_x, _y: screen_y}]. _x/_y is the row center click point.
    """
    s = max((table_rect.right - table_rect.left) / BASE_WIDTH, 0.5)
    column_zones = [(x0 * s, x1 * s, nm) for (x0, x1), nm in zip(BASE_ZONES, COL_NAMES)]
    all_words = []
    for line in raw.get("lines", []):
        for word in line.get("words", []):
            all_words.append(word)
    all_words.sort(key=lambda w: w["bounding_rect"]["y"])
    grouped, cur, cur_y = [], [], None
    for w in all_words:
        y = w["bounding_rect"]["y"]
        if cur_y is None or abs(y - cur_y) <= 10:
            cur.append(w)
            if cur_y is None:
                cur_y = y
        else:
            grouped.append(cur)
            cur, cur_y = [w], y
    if cur:
        grouped.append(cur)
    header_idx = None
    for i, line_words in enumerate(grouped):
        blob = " ".join(w["text"] for w in line_words).lower()
        if "city" in blob and "name" in blob:
            header_idx = i
            break
    if header_idx is None:
        for i, line_words in enumerate(grouped):
            avg_y = sum(w["bounding_rect"]["y"] for w in line_words) / len(line_words)
            if avg_y < 30:
                header_idx = i
                break
    margin = 0
    if header_idx is not None:
        try:
            margin = min(w["bounding_rect"]["x"] for w in grouped[header_idx])
        except Exception:
            margin = 0
    rows = []
    for idx, line_words in enumerate(grouped):
        if header_idx is not None and idx <= header_idx:
            continue
        avg_y = sum(w["bounding_rect"]["y"] for w in line_words) / len(line_words)
        if header_idx is None and avg_y < 20:
            continue
        if avg_y > img_height - 60:
            continue
        if "cancel" in " ".join(w["text"] for w in line_words).lower():
            continue
        row = {name: "" for name in COL_NAMES}
        xs, ys = [], []
        for w in line_words:
            wb = w["bounding_rect"]
            xs.append(wb["x"] + wb["width"] / 2)
            ys.append(wb["y"] + wb["height"] / 2)
            xx = wb["x"] - margin
            for x_min, x_max, col in column_zones:
                if x_min <= xx < x_max:
                    row[col] = (row[col] + " " + w["text"]).strip()
                    break
        if not any(row.values()):
            continue
        row["_x"] = int(table_rect.left + sum(xs) / len(xs))
        row["_y"] = int(table_rect.top + sum(ys) / len(ys))
        rows.append(row)
    return rows


def read_table(pane):
    """Capture + format in one call for page objects."""
    raw, rect = capture_raw(pane)
    try:
        h = raw.get("image_size", {}).get("height", 0) or 0
    except Exception:
        h = 0
    if not h:
        # Fallback: pane height in screen px equals image px at scale 1.
        h = rect.bottom - rect.top
    return reconstruct_table(raw, rect, h)


def read_product_table(pane):
    """Capture + product-row format. Rows are {text, _x, _y}, no column split."""
    raw, rect = capture_raw(pane)
    return reconstruct_product_rows(raw, rect)


def reconstruct_product_rows(raw, table_rect):
    """Y-cluster words into lines. Skips header (Item No./Price) and OK/Cancel footer."""
    all_words = []
    for line in raw.get("lines", []):
        for word in line.get("words", []):
            all_words.append(word)
    all_words.sort(key=lambda w: w["bounding_rect"]["y"])
    grouped, cur, cur_y = [], [], None
    for w in all_words:
        y = w["bounding_rect"]["y"]
        if cur_y is None or abs(y - cur_y) <= 10:
            cur.append(w)
            if cur_y is None:
                cur_y = y
        else:
            grouped.append(cur)
            cur, cur_y = [w], y
    if cur:
        grouped.append(cur)
    rows = []
    for line_words in grouped:
        text = " ".join(w["text"] for w in line_words)
        blob = text.lower()
        if "search:" in blob:
            continue
        if "item no" in blob and "price" in blob:
            continue
        if blob.strip().lower() in ("ok", "cancel") or ("ok" in blob and "cancel" in blob):
            continue
        if not text.strip():
            continue
        xs = [w["bounding_rect"]["x"] + w["bounding_rect"]["width"] / 2 for w in line_words]
        ys = [w["bounding_rect"]["y"] + w["bounding_rect"]["height"] / 2 for w in line_words]
        rows.append({
            "text": text.strip(),
            "_x": int(table_rect.left + sum(xs) / len(xs)),
            "_y": int(table_rect.top + sum(ys) / len(ys)),
        })
    return rows


DOC_COLUMNS = ["Document", "Date", "Name", "State", "Total", "Printed"]


def read_doc_table(pane):
    """Preprocessed capture + documents-row format. Returns [{col: text}]."""
    from .capture import capture_preprocessed
    raw, rect, scale = capture_preprocessed(pane)
    return reconstruct_doc_rows(raw, rect, scale=scale)


def reconstruct_doc_rows(raw, table_rect, scale=1):
    """Header-anchored column split for the Documents/Orders table."""
    all_words = []
    for line in raw.get("lines", []):
        for word in line.get("words", []):
            wb = word["bounding_rect"]
            all_words.append({"text": word["text"],
                              "cx": (wb["x"] + wb["width"] / 2) / scale,
                              "cy": (wb["y"] + wb["height"] / 2) / scale})
    headers = {}
    for w in all_words:
        t = " ".join(w["text"].strip().lower().split())
        for col in DOC_COLUMNS:
            if col in headers:
                continue
            c = col.lower()
            if t == c or (len(t) >= 3 and (c.startswith(t) or t.startswith(c))):
                headers[col] = w["cx"]
    if "Document" not in headers:
        raise RuntimeError(f"orders headers unreadable {sorted(headers)} - needs review")
    edges = sorted(headers.values())
    keys = sorted(headers, key=lambda c: headers[c])
    bands = {}
    for i, col in enumerate(keys):
        lo = (edges[i - 1] + edges[i]) / 2 if i else 0
        hi = (edges[i] + edges[i + 1]) / 2 if i + 1 < len(edges) else 10 ** 9
        bands[col] = (lo, hi)
    head_y = max(headers.values()) and sum(
        w["cy"] for w in all_words
        if " ".join(w["text"].strip().lower().split()) in [c.lower() for c in headers]) / max(len(headers), 1)
    body = [w for w in all_words if w["cy"] > head_y + 8]
    body.sort(key=lambda w: w["cy"])
    grouped, cur, cur_y = [], [], None
    for w in body:
        if cur_y is None or abs(w["cy"] - cur_y) <= 9:
            cur.append(w)
            if cur_y is None:
                cur_y = w["cy"]
        else:
            grouped.append(cur)
            cur, cur_y = [w], w["cy"]
    if cur:
        grouped.append(cur)
    rows = []
    for g in grouped:
        row = {}
        for w in g:
            for col, (lo, hi) in bands.items():
                if lo <= w["cx"] < hi:
                    row[col] = (row.get(col, "") + " " + w["text"]).strip()
                    break
        if not row.get("Document"):
            continue
        rows.append(row)
    return rows

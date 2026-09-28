"""Order line cache: read the table once, update by sku, app recalcs the rest."""
from .items import read_items, set_cell


def _key(sku: str) -> str:
    return (sku or "").strip().upper().replace("O", "0").replace("I", "1")


class ProductItems:
    """productitems[{sku: {pos, COL: {value, x, y}}}]. Missing key triggers one table read."""

    def __init__(self, order):
        self.order = order
        self.productitems = []

    def _resync(self):
        from .items import COLUMNS
        found = []
        for r in read_items(self.order):
            sku = ""
            for col in ("Item No.", "Name"):
                cell = r.cells.get(col)
                if cell is not None and cell.value.strip():
                    sku = cell.value.strip()
                    break
            cols = {}
            for col in COLUMNS:
                cell = r.cells.get(col)
                if cell is None:
                    continue
                cols[col] = {"value": cell.value, "x": cell.x, "y": cell.y}
            found.append({sku: {"pos": r.pos, **cols}})
        self.productitems = found

    def _lookup(self, sku):
        want = _key(sku)
        for entry in self.productitems:
            for k, v in entry.items():
                kk = _key(k)
                if kk == want:
                    return v
                if len(want) >= 6 and len(kk) >= 6 and (want in kk or kk in want):
                    return v
        return None

    def update_quantity(self, sku, qty):
        from .items import set_cell_at
        hit = self._lookup(sku)
        if hit is None:
            self._resync()
            hit = self._lookup(sku)
        if hit is None:
            raise RuntimeError(f"sku '{sku}' not in table - needs review")
        cell = hit.get("Qty.", {})
        set_cell_at(self.order, cell["x"], cell["y"], qty)
        cell["value"] = qty
        return True

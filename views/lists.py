"""Bottom lists panel: Documents / Products / Debtors views over the lower TabControl."""
import time

DOC_COLUMNS = ["Document", "Date", "Name", "State", "Total", "Printed"]


class DocumentRow:
    """One Orders table row as an object. Empty string means OCR missed the cell."""

    def __init__(self, cells=None):
        cells = cells or {}
        self.document = cells.get("Document", "")
        self.date = cells.get("Date", "")
        self.name = cells.get("Name", "")
        self.state = cells.get("State", "")
        self.total = cells.get("Total", "")
        self.printed = cells.get("Printed", "")

    def as_dict(self):
        return {"document": self.document, "date": self.date, "name": self.name,
                "state": self.state, "total": self.total, "printed": self.printed}

    def __repr__(self):
        return f"DocumentRow({self.as_dict()})"


class BottomPanel:
    """The lower TabControl (lists area). Separate from the document tab folder."""

    def __init__(self, app):
        self.app = app

    def folder(self):
        """Fresh lower TabControl: the one that is NOT the document folder."""
        found = []

        def walk(c, d):
            if d > 6:
                return
            try:
                if c.ControlTypeName == "TabControl":
                    found.append(c)
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(self.app.window, 0)
        doc = self.app.doc_tab_folder()
        try:
            doc_id = doc.GetRuntimeId()
        except Exception:
            doc_id = None
        for tc in found:
            try:
                if doc_id is not None and tc.GetRuntimeId() == doc_id:
                    continue
            except Exception:
                pass
            names = [(k.Name or "") for k in tc.GetChildren()
                     if k.ControlTypeName == "TabItemControl"]
            if "Documents" in names:
                return tc
        raise RuntimeError("Bottom lists folder not found - needs review")

    def select_tab(self, name):
        folder = self.folder()
        for k in folder.GetChildren():
            try:
                if k.ControlTypeName == "TabItemControl" and k.Name == name:
                    try:
                        if k.GetSelectionItemPattern().IsSelected:
                            return folder
                    except Exception:
                        pass
                    k.Click()
                    time.sleep(0.4)
                    return folder
            except Exception:
                continue
        raise RuntimeError(f"Bottom tab '{name}' not found - needs review")

    def _nav_entry(self, name):
        """Left Data navigation text (e.g. Documents). Window-wide: bottom tabs are TabItems."""
        found = []

        def walk(c, d):
            if d > 10 or found:
                return
            try:
                if c.ControlTypeName == "TextControl" and (c.Name or "") == name:
                    found.append(c)
                    return
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(self.app.window, 0)
        if not found:
            raise RuntimeError(f"Data nav '{name}' not found - needs review")
        return found[0]

    def ensure_tab(self, name, timeout=5.0):
        """Selects the bottom tab. Opens it via left Data nav when not open yet."""
        try:
            return self.select_tab(name)
        except Exception:
            pass
        entry = self._nav_entry(name)
        try:
            entry.GetLegacyIAccessiblePattern().DoDefaultAction()
        except Exception:
            entry.Click()
        end = time.time() + timeout
        while time.time() < end:
            try:
                return self.select_tab(name)
            except Exception:
                time.sleep(0.3)
        raise RuntimeError(f"Bottom tab '{name}' did not open - needs review")

    def body(self, tab_name):
        """Direct Documents/Creditors/... pane of the bottom folder."""
        folder = self.ensure_tab(tab_name)
        for c in folder.GetChildren():
            try:
                if c.ControlTypeName == "PaneControl" and (c.Name or "") == tab_name:
                    return c
            except Exception:
                continue
        raise RuntimeError(f"Bottom pane '{tab_name}' not found - needs review")


class DocumentsView:
    """Data > Documents list. Only orders implemented, rest is stubbed."""

    def __init__(self, app):
        self.panel = BottomPanel(app)

    def _tree_select(self, body, name):
        for c in body.GetChildren():
            try:
                if c.ControlTypeName == "TreeControl":
                    for item in c.GetChildren():
                        if item.ControlTypeName == "TreeItemControl" and item.Name == name:
                            item.Click()
                            time.sleep(0.5)
                            return
            except Exception:
                continue
        # Deep fallback.
        def walk(c, d):
            if d > 10:
                return False
            try:
                if c.ControlTypeName == "TreeItemControl" and c.Name == name:
                    c.Click()
                    time.sleep(0.5)
                    return True
                for k in c.GetChildren():
                    if walk(k, d + 1):
                        return True
            except Exception:
                pass
            return False
        if not walk(body, 0):
            raise RuntimeError(f"Tree node '{name}' not found - needs review")

    def _table_pane(self, body):
        tree_right = 0

        def find_tree(c, d):
            nonlocal tree_right
            if d > 12:
                return
            try:
                if c.ControlTypeName == "TreeControl":
                    r = c.BoundingRectangle
                    tree_right = max(tree_right, r.right)
                    return
                for k in c.GetChildren():
                    find_tree(k, d + 1)
            except Exception:
                pass

        def has_tree(c, d=0):
            if d > 12:
                return False
            try:
                if c.ControlTypeName == "TreeControl":
                    return True
                return any(has_tree(k, d + 1) for k in c.GetChildren())
            except Exception:
                return False

        find_tree(body, 0)
        best, best_area = None, -1

        def walk(c, d):
            nonlocal best, best_area
            if d > 12:
                return
            try:
                if c.ControlTypeName == "PaneControl" and not has_tree(c):
                    r = c.BoundingRectangle
                    if r.left >= tree_right - 100:
                        area = (r.right - r.left) * (r.bottom - r.top)
                        if area > 80000 and area > best_area:
                            best, best_area = c, area
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(body, 0)
        if best is None:
            raise RuntimeError("Documents table pane not found - needs review")
        return best

    @property
    def orders(self) -> list:
        """Reads the Orders table unfiltered. Returns [DocumentRow]."""
        from ocr.format import read_doc_table
        body = self.panel.body("Documents")
        self._tree_select(body, "Orders")
        self._clear_search(body)
        last = None
        for _ in range(3):
            try:
                return [DocumentRow(c) for c in read_doc_table(self._table_pane(body))]
            except Exception as e:
                last = e
                time.sleep(0.3)
        raise last

    @staticmethod
    def _doc_norm(s: str) -> str:
        return (s or "").upper().replace("O", "0").replace("I", "1").replace("L", "1")

    def _clear_search(self, body):
        edits = []

        def walk(c, d):
            if d > 10:
                return
            try:
                if c.ControlTypeName == "EditControl":
                    edits.append(c)
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(body, 0)
        if edits:
            edits[0].Click()
            edits[0].SendKeys("{Ctrl}a{Del}")
            time.sleep(1.0)

    def find_order(self, number: str):
        """Finds one order by document number only. Returns (DocumentRow, how)."""
        from ocr.format import read_doc_table
        body = self.panel.body("Documents")
        self._tree_select(body, "Orders")
        self._clear_search(body)
        key = self._doc_norm(number.strip())
        last = None
        for _ in range(2):
            try:
                for r in read_doc_table(self._table_pane(body)):
                    if self._doc_norm(r.get("Document", "")) == key:
                        return (DocumentRow(r), "number")
            except Exception as e:
                last = e
            time.sleep(0.3)
        # Fallback: filter narrows to one highlighted row; confirm the rest.
        edits = []

        def walk(c, d):
            if d > 10:
                return
            try:
                if c.ControlTypeName == "EditControl":
                    edits.append(c)
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(body, 0)
        if edits:
            edits[0].Click()
            edits[0].SendKeys("{Ctrl}a{Del}")
            edits[0].SendKeys(number)
            time.sleep(1.0)
        for _ in range(3):
            try:
                rows = [DocumentRow(r) for r in read_doc_table(self._table_pane(body))]
                cands = [r for r in rows if r.state.lower() == "open"]
                if len(cands) == 1:
                    return (cands[0], "filtered")
                if cands:
                    return (cands, "ambiguous")
                return ([], "empty")
            except Exception as e:
                last = e
                time.sleep(0.3)
        raise last

    # ---- stubs: structure only, implemented later ----
    @property
    def confirmations(self):
        raise NotImplementedError("confirmations list later")

    @property
    def invoices(self):
        raise NotImplementedError("invoices list later")


class ProductsView:
    """Mocked for structure. Implemented later."""

    def __init__(self, app):
        self.app = app

    def all(self):
        raise NotImplementedError("products list later")


class DebtorsView:
    """Mocked for structure. Implemented later."""

    def __init__(self, app):
        self.app = app

    def all(self):
        raise NotImplementedError("debtors list later")

"""Order page: form fields + address dialog. OCR lives in ocr/, validation in debtor.py."""
import time
import uiautomation as auto

from .base import BasePage
from .debtor import Debtor, row_matches, doc_matches
from ocr import read_table


class OrderPage(BasePage):
    def __init__(self, app, tab_control):
        super().__init__(app, tab_control)
        self._order_no = None  # identity cache: refreshed on read and after save

    def _order_no_edit(self):
        self.select()
        root = self.root
        label = root.TextControl(Name="No.")
        if not label.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("No. label not found under order root.")
        lr = label.BoundingRectangle
        best, best_dx = None, 10 ** 9
        for c in self._descendants(root):
            try:
                if c.ControlTypeName != "EditControl" or c.Name:
                    continue
                r = c.BoundingRectangle
                if (r.right - r.left) < 50 or (r.bottom - r.top) < 10:
                    continue
                if min(r.bottom, lr.bottom) - max(r.top, lr.top) < 5:
                    continue
                dx = r.left - lr.right
                if dx < -5:
                    continue
                if dx < best_dx:
                    best, best_dx = c, dx
            except Exception:
                continue
        if best is None:
            raise RuntimeError("Order number edit not found.")
        return best

    def _read_order_no(self) -> str:
        """Private. Only called from save: the number is reused while unsaved."""
        try:
            return self._order_no_edit().GetValuePattern().Value or ""
        except Exception:
            return ""

    @property
    def order_no(self) -> str:
        """Cached identity, set only by save(). Empty string means not saved yet."""
        return self._order_no or ""

    def _after_save(self):
        self._order_no = self._read_order_no()
        return self._order_no

    def _cust_ref_edit(self):
        self.select()
        edit = self.root.EditControl(Name="Cust.Ref.")
        if not edit.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Cust.Ref. edit not found under order root.")
        return edit

    def set_cust_ref(self, value: str):
        edit = self._cust_ref_edit()
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        edit.SendKeys(value)
        return self

    def get_cust_ref(self) -> str:
        edit = self._cust_ref_edit()
        try:
            return edit.GetValuePattern().Value or ""
        except Exception:
            return ""

    def _date_edit(self):
        self.select()
        root = self.root
        label = root.TextControl(Name="Date")
        if not label.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Date label not found under order root.")
        lr = label.BoundingRectangle
        best, best_dx = None, 10 ** 9
        for c in self._descendants(root):
            try:
                if c.ControlTypeName != "EditControl" or c.Name:
                    continue
                r = c.BoundingRectangle
                if (r.right - r.left) < 50 or (r.bottom - r.top) < 10:
                    continue
                if min(r.bottom, lr.bottom) - max(r.top, lr.top) < 5:
                    continue
                dx = r.left - lr.right
                if dx < -5:
                    continue
                if dx < best_dx:
                    best, best_dx = c, dx
            except Exception:
                continue
        if best is None:
            raise RuntimeError("Date edit not found next to Date label.")
        return best

    def get_date(self) -> str:
        try:
            return self._date_edit().GetValuePattern().Value or ""
        except Exception:
            return ""

    def set_date(self, value: str):
        edit = self._date_edit()
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        edit.SendKeys(value)
        return self

    def get_address(self) -> str:
        """Read-only debtor address document under the Address label."""
        self.select()
        root = self.root
        label = root.TextControl(Name="Address")
        if not label.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Address label not found under order root.")
        lr = label.BoundingRectangle
        best, best_gap = None, 10 ** 9
        for c in self._descendants(root):
            try:
                if c.ControlTypeName != "EditControl" or c.Name:
                    continue
                r = c.BoundingRectangle
                if (r.right - r.left) < 100 or (r.bottom - r.top) < 40:
                    continue
                gap = r.top - lr.bottom
                if gap < -30:
                    continue
                if gap < best_gap:
                    best, best_gap = c, gap
            except Exception:
                continue
        if best is None:
            raise RuntimeError("Address document not found.")
        try:
            return best.GetValuePattern().Value or ""
        except Exception:
            return ""

    def open_select_debtor(self):
        """Clicks the Address search image. Returns the modal dialog control."""
        self.select()
        root = self.root
        label = root.TextControl(Name="Address")
        if not label.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Address label not found.")
        lr = label.BoundingRectangle
        cands = []
        for c in self._descendants(root):
            try:
                if c.ControlTypeName != "ImageControl":
                    continue
                r = c.BoundingRectangle
                if (r.right - r.left) < 8 or (r.bottom - r.top) < 8:
                    continue
                dx, dy = r.left - lr.right, r.top - lr.top
                if -80 < dx < 80 and -10 < dy < 120:
                    cands.append((dy, dx, c))
            except Exception:
                continue
        if not cands:
            raise RuntimeError("Address search image not found.")
        cands.sort(key=lambda t: (t[0], t[1]))
        cands[0][2].Click()
        time.sleep(0.8)
        for _ in range(10):
            try:
                for w in self.app.window.GetChildren():
                    try:
                        nm = (w.Name or "").lower()
                        if "address" in nm or "select" in nm:
                            return w
                    except Exception:
                        continue
                dlg = self.app.window.WindowControl(SubName="address")
                if dlg.Exists(maxSearchSeconds=0.2):
                    return dlg
                dlg2 = self.app.window.WindowControl(SubName="Select")
                if dlg2.Exists(maxSearchSeconds=0.2):
                    return dlg2
            except Exception:
                pass
            time.sleep(0.2)
        return None

    def _header_combos(self):
        self.select()
        root = self.root
        combos = []
        for c in self._descendants(root):
            try:
                if c.ControlTypeName == "ComboBoxControl" and not c.Name:
                    if (c.BoundingRectangle.bottom - c.BoundingRectangle.top) >= 10:
                        combos.append(c)
            except Exception:
                continue
        combos.sort(key=lambda c: (c.BoundingRectangle.top, c.BoundingRectangle.left))
        return combos

    def _consultant_edit(self):
        self.select()
        edit = self.root.EditControl(Name="Consultant")
        if not edit.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Consultant edit not found under order root.")
        return edit

    def get_consultant(self) -> str:
        try:
            return self._consultant_edit().GetValuePattern().Value or ""
        except Exception:
            return ""

    def set_consultant(self, value: str):
        edit = self._consultant_edit()
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        edit.SendKeys(value)
        return self

    def _vat_combo(self):
        self.select()
        combo = self.root.ComboBoxControl(Name="VAT")
        if not combo.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("VAT combo not found under order root.")
        return combo

    def get_vat(self) -> str:
        combo = self._vat_combo()
        try:
            v = combo.GetValuePattern().Value
            if v:
                return v
        except Exception:
            pass
        try:
            t = combo.TextControl()
            if t.Exists(maxSearchSeconds=0.5):
                return t.Name or ""
        except Exception:
            pass
        return ""

    def _pick_popup_item(self, value: str):
        import time as _t

        def _use(item):
            try:
                item.GetScrollItemPattern().ScrollIntoView()
            except Exception:
                pass
            try:
                item.GetSelectionItemPattern().Select()
                return
            except Exception:
                pass
            item.Click()

        item = self.app.window.ListItemControl(Name=value)
        if item.Exists(maxSearchSeconds=2.0):
            _use(item)
        else:
            item2 = auto.GetRootControl().ListItemControl(Name=value)
            if not item2.Exists(maxSearchSeconds=2.0):
                raise RuntimeError(f"Popup item '{value}' not found.")
            _use(item2)
        end = _t.time() + 2.0
        while _t.time() < end:
            try:
                if not self.app.window.ListItemControl(Name=value).Exists(maxSearchSeconds=0.2):
                    return
            except Exception:
                return
            _t.sleep(0.2)
        try:
            auto.SendKeys("{Esc}")
            _t.sleep(0.3)
        except Exception:
            pass

    def set_vat(self, value: str):
        combo = self._vat_combo()
        opener = combo.ButtonControl(Name="Open")
        if not opener.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("VAT Open button not found.")
        opener.Click()
        time.sleep(0.5)
        self._pick_popup_item(value)
        time.sleep(0.4)
        return self

    def _gross_net_combo(self):
        combos = self._header_combos()
        if not combos:
            raise RuntimeError("Header combo not found under order root.")
        return combos[0]

    def get_gross_net(self) -> str:
        combo = self._gross_net_combo()
        try:
            v = combo.GetValuePattern().Value
            if v:
                return v
        except Exception:
            pass
        try:
            t = combo.TextControl()
            if t.Exists(maxSearchSeconds=0.5):
                return t.Name or ""
        except Exception:
            pass
        return ""

    def set_gross_net(self, value: str):
        self.select()
        combo = self._gross_net_combo()
        opener = combo.ButtonControl(Name="Open")
        if not opener.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Combo Open button not found.")
        opener.Click()
        time.sleep(0.5)
        self._pick_popup_item(value)
        time.sleep(0.4)
        return self

    def dialog_search(self, dlg, text: str):
        """Types into the dialog search edit. The table filters automatically; Find does nothing."""
        edit = None
        edits = []

        def walk(c, d):
            if d > 12:
                return
            try:
                if c.ControlTypeName == "EditControl":
                    edits.append(c)
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(dlg, 0)
        if not edits:
            raise RuntimeError("Dialog search edit not found.")
        edit = edits[0]
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        if text:
            edit.SendKeys(text)
        time.sleep(1.0)
        return dlg

    def close_dialog(self, dlg=None):
        try:
            if dlg is not None:
                cancel = dlg.ButtonControl(Name="Cancel")
                if cancel.Exists(maxSearchSeconds=0.5):
                    cancel.Click()
                    time.sleep(0.4)
                    return
        except Exception:
            pass
        try:
            auto.SendKeys("{Esc}")
            time.sleep(0.4)
        except Exception:
            pass

    def dialog_table_pane(self, dlg):
        """Largest pane inside the dialog = canvas table. UIA only, no OCR."""
        best, best_area = None, -1

        def walk(c, d):
            nonlocal best, best_area
            if d > 12:
                return
            try:
                if c.ControlTypeName == "PaneControl":
                    try:
                        r = c.BoundingRectangle
                        area = (r.right - r.left) * (r.bottom - r.top)
                        if area > best_area:
                            best_area, best = area, c
                    except Exception:
                        pass
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(dlg, 0)
        if best is None:
            raise RuntimeError("Debtor table pane not found.")
        return best

    def dialog_table_rows(self, dlg):
        """Thin wrapper: OCR capture + format live in ocr/. Retries stale COM refs."""
        import time
        last = None
        for _ in range(3):
            try:
                return read_table(self.dialog_table_pane(dlg))
            except Exception as e:
                last = e
                time.sleep(0.3)
        raise last

    def _dismiss_warning(self, max_clicks=3, timeout=3.0):
        """Clicks OK on the 'Net values are used!' warning up to 3 times.

        The dialog wrapper is re-found every check: a stale wrapper keeps
        reporting Exists after the real dialog closed. Returns (clicks, still_present).
        """
        import time
        clicks = 0
        end = time.time() + timeout + max_clicks * 2.0
        while time.time() < end and clicks < max_clicks:
            try:
                warn = self.app.window.WindowControl(SubName="Warning")
                if not warn.Exists(maxSearchSeconds=0.3):
                    return (clicks, False)
                ok = warn.ButtonControl(Name="OK")
                if ok.Exists(maxSearchSeconds=0.3):
                    try:
                        ok.Click()
                    except Exception:
                        return (clicks, False)
                else:
                    warn.SetActive()
                    import uiautomation as auto
                    auto.SendKeys("{Enter}")
                clicks += 1
                time.sleep(0.6)
            except Exception:
                time.sleep(0.2)
        try:
            fresh = self.app.window.WindowControl(SubName="Warning")
            still = fresh.Exists(maxSearchSeconds=0.3)
        except Exception:
            still = False
        return (clicks, bool(still))

    def _discount_edit(self):
        self.select()
        edit = self.root.EditControl(Name="Discount")
        if not edit.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Discount edit not found under order root.")
        return edit

    def get_discount(self) -> str:
        try:
            return self._discount_edit().GetValuePattern().Value or ""
        except Exception:
            return ""

    def set_discount(self, value: str):
        edit = self._discount_edit()
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        edit.SendKeys(value)
        edit.SendKeys("{Tab}")
        return self

    def _shipping_value_edit(self):
        """Unlabeled numerical edit directly above the totals-area VAT text."""
        self.select()
        root = self.root
        labels = [c for c in self._descendants(root)
                  if c.ControlTypeName == "TextControl" and c.Name == "VAT"]
        if not labels:
            raise RuntimeError("VAT label not found under order root.")
        lr = sorted(labels, key=lambda c: c.BoundingRectangle.top)[-1].BoundingRectangle
        best, best_gap = None, 10 ** 9
        for c in self._descendants(root):
            try:
                if c.ControlTypeName != "EditControl" or c.Name:
                    continue
                r = c.BoundingRectangle
                if (r.right - r.left) < 40 or (r.bottom - r.top) < 10:
                    continue
                gap = lr.top - r.bottom
                if gap < -5:
                    continue
                if gap < best_gap:
                    best, best_gap = c, gap
            except Exception:
                continue
        if best is None:
            raise RuntimeError("Shipping value edit not found.")
        return best

    def get_shipping_value(self) -> str:
        try:
            return self._shipping_value_edit().GetValuePattern().Value or ""
        except Exception:
            return ""

    def set_shipping_value(self, value: str):
        edit = self._shipping_value_edit()
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        edit.SendKeys(value)
        edit.SendKeys("{Tab}")
        return self

    def _shipping_combo(self):
        self.select()
        combo = self.root.ComboBoxControl(Name="Shipping")
        if not combo.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Shipping combo not found under order root.")
        return combo

    def get_shipping_type(self) -> str:
        combo = self._shipping_combo()
        try:
            v = combo.GetValuePattern().Value
            if v:
                return v
        except Exception:
            pass
        try:
            t = combo.EditControl()
            if t.Exists(maxSearchSeconds=0.5):
                return t.GetValuePattern().Value or ""
        except Exception:
            pass
        return ""

    def set_shipping_type(self, value: str):
        combo = self._shipping_combo()
        opener = combo.ButtonControl(Name="Open")
        if not opener.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Shipping Open button not found.")
        opener.Click()
        import time
        time.sleep(0.5)
        self._pick_popup_item(value)
        time.sleep(0.4)
        return self

    def list_shipping_types(self) -> list:
        """Opens the Shipping combo and returns all popup item names. Closes with Escape."""
        import uiautomation as auto
        self.select()
        combo = self._shipping_combo()
        opener = combo.ButtonControl(Name="Open")
        if not opener.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Shipping Open button not found.")
        opener.Click()
        import time
        time.sleep(0.6)
        names = []
        for scope in (self.app.window, auto.GetRootControl()):
            try:
                lst = scope.ListControl(Name="Shipping")
                if lst.Exists(maxSearchSeconds=1.0):
                    for it in lst.GetChildren():
                        try:
                            if it.ControlTypeName == "ListItemControl" and it.Name:
                                names.append(it.Name)
                        except Exception:
                            continue
                    break
            except Exception:
                continue
        try:
            auto.SendKeys("{Esc}")
            time.sleep(0.3)
        except Exception:
            pass
        return names

    def get_remarks(self) -> str:
        """Read-only remarks box under the Remarks label."""
        self.select()
        root = self.root
        label = root.TextControl(Name="Remarks")
        if not label.Exists(maxSearchSeconds=1.0):
            return ""
        lr = label.BoundingRectangle
        best, best_gap = None, 10 ** 9
        for c in self._descendants(root):
            try:
                if c.ControlTypeName != "EditControl" or c.Name:
                    continue
                r = c.BoundingRectangle
                if (r.right - r.left) < 100 or (r.bottom - r.top) < 30:
                    continue
                gap = r.top - lr.bottom
                if gap < -30:
                    continue
                if gap < best_gap:
                    best, best_gap = c, gap
            except Exception:
                continue
        if best is None:
            return ""
        try:
            return best.GetValuePattern().Value or ""
        except Exception:
            return ""

    def get_value(self):
        """Full order snapshot for reading and checking. No coordinates."""
        from .order_value import build_order_value
        self.select()
        return build_order_value(self)

    @property
    def productItems(self):
        from .product_items import ProductItems
        if self.__dict__.get("_product_items") is None:
            self.__dict__["_product_items"] = ProductItems(self)
        return self.__dict__["_product_items"]

    def open_select_product(self):
        """Clicks the first gutter image below Items. Returns the dialog control."""
        import time
        self.select()
        root = self.root
        label = root.TextControl(Name="Items")
        if not label.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Items label not found - needs review")
        lr = label.BoundingRectangle
        best, best_dy = None, 10 ** 9
        for c in self._descendants(root):
            try:
                if c.ControlTypeName != "ImageControl":
                    continue
                r = c.BoundingRectangle
                if (r.right - r.left) < 16 or (r.bottom - r.top) < 16:
                    continue
                dy = r.top - lr.top
                if -10 < dy < 200 and dy < best_dy:
                    best, best_dy = c, dy
            except Exception:
                continue
        if best is None:
            raise RuntimeError("Items gutter image not found - needs review")
        best.Click()
        time.sleep(1.0)
        for _ in range(10):
            try:
                dlg = self.app.window.WindowControl(SubName="Select a product")
                if dlg.Exists(maxSearchSeconds=0.2):
                    return dlg
            except Exception:
                pass
            time.sleep(0.2)
        return None

    def dialog_product_search(self, dlg, text: str):
        """Types into Search and presses Find (visible button in this dialog)."""
        import time
        edits = []

        def walk(c, d):
            if d > 14:
                return
            try:
                if c.ControlTypeName == "EditControl":
                    edits.append(c)
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(dlg, 0)
        if not edits:
            raise RuntimeError("Product search edit not found - needs review")
        edit = edits[0]
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        if text:
            edit.SendKeys(text)
        find = dlg.ButtonControl(Name="Find")
        if find.Exists(maxSearchSeconds=1.0):
            find.Click()
        time.sleep(1.0)
        return dlg

    def dialog_product_rows(self, dlg):
        """Thin wrapper: OCR capture + product-row format."""
        from ocr import read_product_table
        import time
        last = None
        for _ in range(3):
            try:
                panes = []

                def walk(c, d):
                    if d > 14:
                        return
                    try:
                        if c.ControlTypeName == "PaneControl":
                            panes.append(c)
                        for k in c.GetChildren():
                            walk(k, d + 1)
                    except Exception:
                        pass

                walk(dlg, 0)
                panes.sort(key=lambda c: (c.BoundingRectangle.right - c.BoundingRectangle.left)
                           * (c.BoundingRectangle.bottom - c.BoundingRectangle.top), reverse=True)
                for pane in panes:
                    try:
                        rows = read_product_table(pane)
                        if rows:
                            return rows
                    except Exception:
                        continue
                return []
            except Exception as e:
                last = e
                time.sleep(0.3)
        raise last

    def close_product_dialog(self, ok=False):
        import time
        import uiautomation as auto
        try:
            dlg = self.app.window.WindowControl(SubName="Select a product")
            btn = dlg.ButtonControl(Name="OK" if ok else "Cancel")
            if btn.Exists(maxSearchSeconds=0.5):
                btn.Click()
                time.sleep(0.4)
                return
        except Exception:
            pass
        try:
            auto.SendKeys("{Esc}")
            time.sleep(0.4)
        except Exception:
            pass

    def select_product(self, ref) -> tuple:
        """Single-transaction product pick. Matches SKU (item number) only."""
        import time
        import ctypes
        from .product import ProductRef
        if isinstance(ref, str):
            ref = ProductRef(item_no=ref)
        if not (ref.item_no or "").strip():
            return ("ERROR", "item number required - needs review")
        key = ref.item_no.strip().upper().replace("O", "0").replace("I", "1")
        self.select()
        try:
            self.close_product_dialog(ok=False)
        except Exception:
            pass
        dlg = self.open_select_product()
        if dlg is None:
            return ("ERROR", "product dialog did not open")
        self.dialog_product_search(dlg, ref.item_no)

        def _ocr_norm(s):
            return (s or "").upper().replace("O", "0").replace("I", "1")

        matches = [r for r in self.dialog_product_rows(dlg) if key in _ocr_norm(r["text"])]
        if not matches:
            self.close_product_dialog(ok=False)
            return ("NOT_FOUND", [])
        if len(matches) > 1:
            self.close_product_dialog(ok=False)
            return ("CONFLICT", matches)
        row = matches[0]
        ctypes.windll.user32.SetCursorPos(row["_x"], row["_y"])
        time.sleep(0.1)
        for _ in range(2):
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.08)
        time.sleep(0.6)
        try:
            still = self.app.window.WindowControl(SubName="Select a product").Exists(maxSearchSeconds=0.5)
        except Exception:
            still = False
        if still:
            ok_btn = dlg.ButtonControl(Name="OK")
            if not ok_btn.Exists(maxSearchSeconds=1.0):
                self.close_product_dialog(ok=False)
                return ("ERROR", "OK button missing - needs review")
            ok_btn.Click()
            time.sleep(0.6)
        return ("SELECTED", {"item_no": ref.item_no, "row_text": row["text"]})

    def list_debtors(self, query: str = "") -> list:
        """Opens the address dialog, searches, OCRs the rows, closes. No selection made."""
        self.select()
        dlg = self.open_select_debtor()
        if dlg is None:
            raise RuntimeError("address dialog did not open")
        try:
            self.dialog_search(dlg, query)
            return self.dialog_table_rows(dlg)
        finally:
            self.close_dialog(dlg)

    def select_debtor(self, debtor) -> tuple:
        """Single-transaction pick with two checks. Returns (status, payload)."""
        import ctypes
        if isinstance(debtor, str):
            debtor = Debtor(company=debtor)
        self.select()
        dlg = self.open_select_debtor()
        if dlg is None:
            return ("ERROR", "address dialog did not open")
        self.dialog_search(dlg, debtor.company or debtor.last_name or debtor.no)
        matches = [row for row in self.dialog_table_rows(dlg) if row_matches(row, debtor)]
        if not matches:
            self.close_dialog(dlg)
            return ("NOT_FOUND", {})
        if len(matches) > 1:
            self.close_dialog(dlg)
            return ("CONFLICT", matches)
        row = matches[0]
        ctypes.windll.user32.SetCursorPos(row["_x"], row["_y"])
        time.sleep(0.1)
        for _ in range(2):
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.08)
        time.sleep(0.8)
        _, warn_still = self._dismiss_warning()
        if warn_still:
            return ("ERROR", "warning dialog persisted after 3 OK clicks - needs review")
        time.sleep(0.4)
        try:
            addr = self.get_address()
        except Exception as e:
            return ("ERROR", f"address unreadable after click: {e}")
        ok, detail = doc_matches(addr, debtor)
        if not ok:
            return ("MISMATCH", {"debtor": debtor.__dict__, "address_text": addr, "detail": detail})
        return ("SELECTED", {**debtor.__dict__, "address_text": addr})

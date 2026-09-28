"""App shell / factory layer. Uses live UIA refs, real toolbar names from scan."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import time
import uiautomation as auto


class FakturamaApp:
    def __init__(self):
        self.window = auto.WindowControl(searchDepth=1, SubName="Fakturama")
        if not self.window.Exists(maxSearchSeconds=5):
            raise RuntimeError("Fakturama window not found. Is it open?")
        self.window.SetActive()
        # Document tab folder = TabControl with most TabItems (skip bottom Documents view).
        self.tab_folder = self.doc_tab_folder()
        if not self.tab_folder.Exists(maxSearchSeconds=3):
            raise RuntimeError("TabControl not found under Fakturama window.")

    def _all_tab_controls(self):
        found = []

        def walk(c, d):
            if d > 8:
                return
            try:
                if c.ControlTypeName == "TabControl":
                    found.append(c)
                for k in c.GetChildren():
                    walk(k, d + 1)
            except Exception:
                pass

        walk(self.window, 0)
        return found

    def doc_tab_folder(self):
        """Fresh document TabControl: the one holding order/product tabs, not the bottom lists view."""
        cands = self._all_tab_controls()
        if not cands:
            raise RuntimeError("Document TabControl not found.")
        for tc in cands:
            try:
                names = [(k.Name or "") for k in tc.GetChildren() if k.ControlTypeName == "TabItemControl"]
            except Exception:
                continue
            if any("New Order" in n or "New product" in n or n.startswith(("INV", "PO", "CONF")) for n in names):
                return tc
        best, best_n = None, -1
        for tc in cands:
            try:
                n = sum(1 for k in tc.GetChildren() if k.ControlTypeName == "TabItemControl")
            except Exception:
                n = 0
            if n > best_n:
                best, best_n = tc, n
        return best

    def _find_button(self, name, timeout=1.0):
        """Deep search for toolbar button by exact Name. Returns control or None."""
        btn = self.window.ButtonControl(Name=name)
        if btn.Exists(maxSearchSeconds=timeout):
            return btn
        return None

    def save_button_exists(self):
        return self._find_button("Save", timeout=0.5) is not None

    @property
    def documents(self):
        from views import DocumentsView
        return DocumentsView(self)

    @property
    def products(self):
        from views import ProductsView
        return ProductsView(self)

    @property
    def debtors(self):
        from views import DebtorsView
        return DebtorsView(self)

    def save_available(self) -> bool:
        """True only when the Save button exists and is enabled. No click made."""
        try:
            btn = self.window.ButtonControl(Name="Save")
            if not btn.Exists(maxSearchSeconds=0.5):
                return False
            try:
                return bool(btn.IsEnabled)
            except Exception:
                return True
        except Exception:
            return False

    def _get_active_tab_ref(self):
        """Live TabItemControl of foreground tab. No names stored."""
        tf = self.doc_tab_folder()
        try:
            sel = tf.GetSelectionPattern().GetSelection()
            if sel:
                return sel[0]
        except Exception:
            pass
        # Fallback: scan TabItems for IsSelected
        for ch in tf.GetChildren():
            try:
                if ch.ControlTypeName == "TabItemControl":
                    pat = ch.GetSelectionItemPattern()
                    if pat and pat.IsSelected:
                        return ch
            except Exception:
                continue
        raise RuntimeError("Could not get active tab reference.")

    def save(self):
        """Pure action: click Save else Ctrl+S. No tab logic here."""
        from pages import BasePage  # noqa - keep layer split, avoid cycle at import time
        btn = self._find_button("Save", timeout=0.5)
        if btn is not None:
            btn.Click()
        else:
            auto.SendKeys("{Ctrl}s")
        time.sleep(0.4)

    def _tab_items(self):
        try:
            return [c for c in self.doc_tab_folder().GetChildren() if c.ControlTypeName == "TabItemControl"]
        except Exception:
            return []

    def _tab_count(self):
        return len(self._tab_items())

    def _wait_new_selection(self, old_name, old_count, timeout=1.0):
        """Fast poll: new tab = count grew OR selected name changed. Same-name tabs exist."""
        import time as _t
        end = _t.time() + timeout
        while _t.time() < end:
            try:
                tf = self.doc_tab_folder()
                sel = tf.GetSelectionPattern().GetSelection()
                if sel:
                    try:
                        n = self._tab_count()
                        if old_count >= 0 and n > old_count:
                            return sel[0]
                    except Exception:
                        pass
                    if sel[0].Name != old_name:
                        return sel[0]
            except Exception:
                pass
            _t.sleep(0.05)
        return self._get_active_tab_ref()

    def create_order(self):
        from pages import OrderPage
        old = self._get_active_tab_ref().Name
        old_count = self._tab_count()
        btn = self._find_button("Order", timeout=2.0)
        if btn is None:
            raise RuntimeError("Toolbar button 'Order' not found (scan shows Name='Order').")
        btn.Click()
        time.sleep(0.1)
        new_ref = self._wait_new_selection(old, old_count)
        return OrderPage(app=self, tab_control=new_ref)

    def create_debtor(self):
        """Contact button opens a context menu; New Debtor opens the debtor page."""
        import uiautomation as auto
        from pages import DebtorPage
        old_count = self._tab_count()
        try:
            old = self._get_active_tab_ref().Name
        except Exception:
            old = ""
        btn = self._find_button("Contact", timeout=2.0)
        if btn is None:
            raise RuntimeError("Toolbar button 'Contact' not found.")
        item = None
        for _ in range(3):
            btn.Click()
            time.sleep(0.6)
            cand = self.window.MenuItemControl(Name="New Debtor")
            if cand.Exists(maxSearchSeconds=1.0):
                item = cand
                break
            desk = auto.GetRootControl().MenuItemControl(Name="New Debtor")
            if desk.Exists(maxSearchSeconds=1.0):
                item = desk
                break
            try:
                auto.SendKeys("{Esc}")
                time.sleep(0.2)
            except Exception:
                pass
        if item is None:
            raise RuntimeError("Menu item 'New Debtor' never opened - needs review")
        item.Click()
        time.sleep(0.6)
        new_ref = self._wait_new_selection(old, old_count)
        try:
            if "Debtor" not in (new_ref.Name or ""):
                raise RuntimeError(f"expected debtor tab, got '{new_ref.Name}' - needs review")
        except RuntimeError:
            raise
        except Exception:
            pass
        return DebtorPage(app=self, tab_control=new_ref)

    def create_product(self):
        from pages import ProductPage
        old = self._get_active_tab_ref().Name
        old_count = self._tab_count()
        btn = self._find_button("Product", timeout=2.0)
        if btn is None:
            raise RuntimeError("Toolbar button 'Product' not found.")
        btn.Click()
        time.sleep(0.1)
        new_ref = self._wait_new_selection(old, old_count)
        return ProductPage(app=self, tab_control=new_ref)

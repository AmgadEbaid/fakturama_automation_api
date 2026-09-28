"""Debtor page: inner tabs Address / Miscellaneous / Notice + Customer ID cached on save."""
import time
import uiautomation as auto

from .base import BasePage
from .address import AddressData, AddressSection
from .misc import MiscData, MiscSection


class InnerSection:
    """Placeholder for Miscellaneous / Notice until their fields are grounded."""

    def __init__(self, page, name):
        self.page = page
        self.section_name = name

    def select(self):
        self.page.select_inner(self.section_name)
        return self


class DebtorPage(BasePage):
    def __init__(self, app, tab_control):
        super().__init__(app, tab_control)
        self._customer_id = None
        self._address = AddressSection(self)
        self._misc = MiscSection(self)

    @property
    def address(self) -> AddressSection:
        return self._address

    @property
    def miscellaneous(self) -> MiscSection:
        return self._misc

    def fill_miscellaneous(self, data: MiscData):
        return self.miscellaneous.fill(data)

    @property
    def notice(self) -> InnerSection:
        return InnerSection(self, "Notice")

    def _inner_tab_item(self, name):
        for c in self._descendants(self.root):
            try:
                if c.ControlTypeName == "TabItemControl" and c.Name == name:
                    return c
            except Exception:
                continue
        return None

    def select_inner(self, name):
        """Clicks an inner tab (Address / Miscellaneous / Notice) of this debtor tab."""
        self.select()
        item = self._inner_tab_item(name)
        if item is None:
            raise RuntimeError(f"Inner tab '{name}' not found - needs review")
        try:
            if item.GetSelectionItemPattern().IsSelected:
                return self
        except Exception:
            pass
        item.Click()
        end = time.time() + 3.0
        while time.time() < end:
            try:
                if self._inner_tab_item(name).GetSelectionItemPattern().IsSelected:
                    time.sleep(0.2)
                    return self
            except Exception:
                pass
            time.sleep(0.2)
        raise RuntimeError(f"Inner tab '{name}' did not activate - needs review")

    def fill_address(self, data: AddressData):
        return self.address.fill(data)

    def fill_delivery_address(self, data: AddressData):
        return self.address.fill_delivery(data)

    def _pick_popup_item(self, value: str):
        import time as _t
        import uiautomation as auto

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
                raise RuntimeError(f"Popup item '{value}' not found - needs review")
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

    def _delivery_checkbox(self):
        cb = self.root.CheckBoxControl(Name="Delivery Address equals Invoice Address")
        if not cb.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Delivery checkbox not found - needs review")
        return cb

    def _ensure_delivery_open(self, timeout=5.0):
        """Unchecks the equals box so the delivery tree opens. No-op when already open."""
        self.select_inner("Address")
        try:
            auto.SendKeys("{Esc}")
            time.sleep(0.2)
        except Exception:
            pass
        cb = self._delivery_checkbox()
        for _ in range(2):
            try:
                if cb.GetTogglePattern().ToggleState != 1:
                    break
            except Exception:
                pass
            cb.Click()
            time.sleep(0.5)
        end = time.time() + timeout
        while time.time() < end:
            try:
                g = self.root.GroupControl(Name="Delivery Address")
                if g.Exists(maxSearchSeconds=0.3):
                    return self
            except Exception:
                pass
            time.sleep(0.2)
        raise RuntimeError("Delivery Address group did not open - needs review")

    @property
    def customer_id(self) -> str:
        """Cached identity, set only by save(). Empty means not saved yet."""
        return self._customer_id or ""

    def _after_save(self):
        try:
            edit = self.root.EditControl(Name="Customer ID")
            self._customer_id = edit.GetValuePattern().Value or "" if edit.Exists(1.0) else ""
        except Exception:
            self._customer_id = ""
        return self._customer_id

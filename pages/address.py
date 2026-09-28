"""Address data + section writer. Invoice and delivery groups share the shape."""
from dataclasses import dataclass


@dataclass
class AddressData:
    """Blank string means leave the field untouched."""
    gender: str = ""
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    street: str = ""
    zip_code: str = ""
    city: str = ""
    country: str = ""
    birthday: str = ""


class AddressSection:
    """Writes a whole AddressData into one group scope. No per-field public API."""

    def __init__(self, page):
        self.page = page

    def _invoice_scope(self):
        root = self.page.root
        g = root.GroupControl(Name="Address")
        if g.Exists(maxSearchSeconds=1.0):
            return g
        return root

    def _delivery_scope(self, timeout=5.0):
        import time
        end = time.time() + timeout
        while time.time() < end:
            try:
                g = self.page.root.GroupControl(Name="Delivery Address")
                if g.Exists(maxSearchSeconds=0.3):
                    return g
            except Exception:
                pass
            time.sleep(0.2)
        raise RuntimeError("Delivery Address group did not open - needs review")

    def _set_edit(self, scope, name, value):
        if not value:
            return
        edit = scope.EditControl(Name=name)
        if not edit.Exists(maxSearchSeconds=1.0):
            raise RuntimeError(f"Edit '{name}' not found - needs review")
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        edit.SendKeys(value)

    def _sibling_edit(self, scope, name):
        """Unlabeled box right after a named edit (last name after first, city after zip)."""
        named = scope.EditControl(Name=name)
        if not named.Exists(maxSearchSeconds=1.0):
            raise RuntimeError(f"Edit '{name}' not found - needs review")
        try:
            nr = named.BoundingRectangle
        except Exception:
            raise RuntimeError(f"Edit '{name}' unreadable - needs review")
        parent = named.GetParentControl()
        best, best_dx = None, 10 ** 9
        for k in parent.GetChildren():
            try:
                if k.ControlTypeName != "EditControl" or k.Name:
                    continue
                r = k.BoundingRectangle
                if min(r.bottom, nr.bottom) - max(r.top, nr.top) < 5:
                    continue
                dx = r.left - nr.right
                if dx < -5 or dx >= best_dx:
                    continue
                best, best_dx = k, dx
            except Exception:
                continue
        if best is None:
            raise RuntimeError(f"Second box after '{name}' not found - needs review")
        return best

    def _set_combo(self, scope, name, value):
        import time
        if not value:
            return
        combo = scope.ComboBoxControl(Name=name)
        if not combo.Exists(maxSearchSeconds=1.0):
            raise RuntimeError(f"Combo '{name}' not found - needs review")
        opener = combo.ButtonControl(Name="Open")
        if not opener.Exists(maxSearchSeconds=1.0):
            raise RuntimeError(f"Combo '{name}' has no Open button - needs review")
        opener.Click()
        time.sleep(0.5)
        self.page._pick_popup_item(value)
        time.sleep(0.4)
        try:
            import uiautomation as auto
            combo.Click()
            auto.SendKeys("{Tab}")
            time.sleep(0.3)
        except Exception:
            pass
        try:
            shown = combo.GetValuePattern().Value or ""
        except Exception:
            shown = ""
        if value.lower() not in shown.lower():
            raise RuntimeError(f"Combo '{name}' did not keep '{value}' - needs review")

    def _set_birthday(self, scope, value):
        if not value:
            return
        label = scope.TextControl(Name="Birthday")
        if not label.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Birthday label not found - needs review")
        lr = label.BoundingRectangle
        best, best_dx = None, 10 ** 9
        for k in self.page._descendants(scope):
            try:
                if k.ControlTypeName != "EditControl" or k.Name:
                    continue
                r = k.BoundingRectangle
                if min(r.bottom, lr.bottom) - max(r.top, lr.top) < 5:
                    continue
                dx = r.left - lr.right
                if dx < -5 or dx >= best_dx:
                    continue
                best, best_dx = k, dx
            except Exception:
                continue
        if best is None:
            raise RuntimeError("Birthday edit not found - needs review")
        best.Click()
        best.SendKeys("{Ctrl}a{Del}")
        best.SendKeys(value)

    def _fill_scope(self, scope, data: AddressData):
        self._set_combo(scope, "Gender", data.gender)
        self._set_edit(scope, "First Name Last Name", data.first_name)
        if data.last_name:
            box = self._sibling_edit(scope, "First Name Last Name")
            box.Click()
            box.SendKeys("{Ctrl}a{Del}")
            box.SendKeys(data.last_name)
        self._set_edit(scope, "Company", data.company)
        self._set_edit(scope, "Street", data.street)
        self._set_edit(scope, "ZIP, City", data.zip_code)
        if data.city:
            box = self._sibling_edit(scope, "ZIP, City")
            box.Click()
            box.SendKeys("{Ctrl}a{Del}")
            box.SendKeys(data.city)
        self._set_combo(scope, "Country", data.country)
        self._set_birthday(scope, data.birthday)

    def fill(self, data: AddressData):
        """Fills the invoice address directly."""
        self.page.select_inner("Address")
        self._fill_scope(self._invoice_scope(), data)
        return self

    def fill_delivery(self, data: AddressData):
        """Unchecks the equals box, waits for the delivery tree, fills it."""
        self.page.select_inner("Address")
        self.page._ensure_delivery_open()
        self._fill_scope(self._delivery_scope(), data)
        return self

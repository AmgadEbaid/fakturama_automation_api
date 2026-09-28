"""Product page: one data object, one fill. Picture section ignored per spec."""
from dataclasses import dataclass
from .base import BasePage


@dataclass
class ProductRef:
    """What identifies a product row. Blank means ignore that key."""
    item_no: str = ""
    name: str = ""


@dataclass
class ProductData:
    """Blank string means leave the field untouched."""
    item_number: str = ""
    name: str = ""
    category: str = ""
    gtin: str = ""
    description: str = ""
    price_gross: str = ""
    cost_net: str = ""
    vat: str = ""
    quantity: str = ""
    udf1: str = ""
    udf2: str = ""
    udf3: str = ""


class ProductPage(BasePage):
    def _set_edit(self, name, value):
        if not value:
            return
        self.select()
        edit = self.root.EditControl(Name=name)
        if not edit.Exists(maxSearchSeconds=1.0):
            raise RuntimeError(f"Edit '{name}' not found - needs review")
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        edit.SendKeys(value)

    def _set_combo(self, name, value):
        import time
        if not value:
            return
        self.select()
        combo = self.root.ComboBoxControl(Name=name)
        if not combo.Exists(maxSearchSeconds=1.0):
            raise RuntimeError(f"Combo '{name}' not found - needs review")
        opener = combo.ButtonControl(Name="Open")
        if not opener.Exists(maxSearchSeconds=1.0):
            raise RuntimeError(f"Combo '{name}' has no Open button - needs review")
        opener.Click()
        time.sleep(0.5)
        import uiautomation as auto
        item = self.app.window.ListItemControl(Name=value)
        if item.Exists(maxSearchSeconds=2.0):
            item.Click()
        else:
            item2 = auto.GetRootControl().ListItemControl(Name=value)
            if not item2.Exists(maxSearchSeconds=2.0):
                raise RuntimeError(f"Popup item '{value}' not found - needs review")
            item2.Click()
        time.sleep(0.4)

    def _set_price_gross(self, value):
        if not value:
            return
        self.select()
        label = self.root.TextControl(Name="Price (gross)")
        if not label.Exists(maxSearchSeconds=1.0):
            raise RuntimeError("Price label not found - needs review")
        lr = label.BoundingRectangle
        best, best_dx = None, 10 ** 9
        for k in self._descendants(self.root):
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
            raise RuntimeError("Price (gross) edit not found - needs review")
        best.Click()
        best.SendKeys("{Ctrl}a{Del}")
        best.SendKeys(value)
        best.SendKeys("{Tab}")

    def fill_product(self, data: ProductData):
        self._set_edit("Item Number", data.item_number)
        self._set_edit("Name", data.name)
        self._set_combo("Category", data.category)
        self._set_edit("GTIN", data.gtin)
        self._set_edit("Description", data.description)
        self._set_price_gross(data.price_gross)
        self._set_edit("cost price (net)", data.cost_net)
        self._set_combo("VAT", data.vat)
        self._set_edit("Quantity", data.quantity)
        self._set_edit("user defined field 1", data.udf1)
        self._set_edit("user defined field 2", data.udf2)
        self._set_edit("user defined field 3", data.udf3)
        return self

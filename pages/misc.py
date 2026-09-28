"""Miscellaneous section: one data object, one fill. No per-field public API."""
from dataclasses import dataclass


@dataclass
class MiscData:
    """Blank string means leave the field untouched."""
    category: str = ""
    supplier_number: str = ""
    email: str = ""
    telephone: str = ""
    telefax: str = ""
    mobile: str = ""
    website: str = ""
    webshop_user: str = ""
    payment: str = ""
    reliability: str = ""
    vat_number: str = ""
    gln: str = ""
    discount: str = ""
    net_or_gross: str = ""


class MiscSection:
    def __init__(self, page):
        self.page = page

    def _scope(self):
        self.page.select_inner("Miscellaneous")
        return self.page.root

    def _set_edit(self, scope, name, value):
        if not value:
            return
        edit = scope.EditControl(Name=name)
        if not edit.Exists(maxSearchSeconds=1.0):
            raise RuntimeError(f"Edit '{name}' not found - needs review")
        edit.Click()
        edit.SendKeys("{Ctrl}a{Del}")
        edit.SendKeys(value)

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

    def fill(self, data: MiscData):
        scope = self._scope()
        self._set_combo(scope, "Category", data.category)
        self._set_edit(scope, "Supplier Number", data.supplier_number)
        self._set_edit(scope, "E-Mail", data.email)
        self._set_edit(scope, "Telephone", data.telephone)
        self._set_edit(scope, "Telefax", data.telefax)
        self._set_edit(scope, "Mobile", data.mobile)
        self._set_edit(scope, "Web Site", data.website)
        self._set_edit(scope, "WebShop user name", data.webshop_user)
        self._set_combo(scope, "Payment", data.payment)
        self._set_combo(scope, "Reliability", data.reliability)
        self._set_edit(scope, "VAT Number", data.vat_number)
        self._set_edit(scope, "GLN", data.gln)
        self._set_edit(scope, "Discount", data.discount)
        self._set_combo(scope, "Net or Gross", data.net_or_gross)
        return self

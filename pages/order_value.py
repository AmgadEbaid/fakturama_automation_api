"""Full order snapshot for reading and checking. No coordinates, no writes."""
from dataclasses import dataclass, field, asdict
import json


@dataclass
class OrderItemValue:
    pos: str = ""
    qty: str = ""
    item_no: str = ""
    name: str = ""
    description: str = ""
    vat: str = ""
    unit_price: str = ""
    discount: str = ""
    price: str = ""


@dataclass
class OrderValue:
    no: str = ""
    cust_ref: str = ""
    date: str = ""
    gross_net: str = ""
    consultant: str = ""
    vat: str = ""
    address_text: str = ""
    address_lines: list = field(default_factory=list)
    discount: str = ""
    shipping_value: str = ""
    shipping_type: str = ""
    remarks: str = ""
    items: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["items"] = [asdict(i) if isinstance(i, OrderItemValue) else i for i in self.items]
        return d

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


def _cell(cells, col):
    cell = cells.get(col)
    return cell.value if cell is not None and hasattr(cell, "value") else ""


def build_order_value(order) -> OrderValue:
    """Reads everything live. Debtor from the document edit, items from OCR without coords."""
    from .items import read_items
    val = OrderValue()
    try:
        val.no = order._order_no_edit().GetValuePattern().Value or ""
    except Exception:
        val.no = ""
    val.cust_ref = order.get_cust_ref()
    val.date = order.get_date()
    val.gross_net = order.get_gross_net()
    val.consultant = order.get_consultant()
    val.vat = order.get_vat()
    try:
        val.address_text = order.get_address()
    except Exception:
        val.address_text = ""
    val.address_lines = [l.strip() for l in val.address_text.replace("\r", "\n").split("\n") if l.strip()]
    val.discount = order.get_discount()
    val.shipping_value = order.get_shipping_value()
    val.shipping_type = order.get_shipping_type()
    try:
        val.remarks = order.get_remarks()
    except Exception:
        val.remarks = ""
    try:
        for r in read_items(order):
            c = r.cells
            val.items.append(OrderItemValue(
                pos=r.pos,
                qty=_cell(c, "Qty."),
                item_no=_cell(c, "Item No."),
                name=_cell(c, "Name"),
                description=_cell(c, "Description"),
                vat=_cell(c, "VAT"),
                unit_price=_cell(c, "U.Price"),
                discount=_cell(c, "Discount"),
                price=_cell(c, "Price"),
            ))
    except Exception as e:
        val.items = [{"error": str(e)[:100]}]
    return val

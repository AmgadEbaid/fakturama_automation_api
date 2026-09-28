import sys
sys.path.insert(0, "getOrderFromImage")
from schema import SalesOrder
from pages import Debtor, AddressData, MiscData, ProductData, LineItem


def split_name(full):
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def debtor_from(o: SalesOrder) -> Debtor:
    first, last = split_name(o.customer.contact_name)
    return Debtor(
        company=o.customer.company,
        first_name=first,
        last_name=last,
        street=o.billing_address.street,
        zip_code=o.billing_address.zip,
        city=o.billing_address.city,
        country=o.billing_address.country,
    )


def billing_from(o: SalesOrder) -> AddressData:
    first, last = split_name(o.customer.contact_name)
    return AddressData(
        first_name=first,
        last_name=last,
        company=o.customer.company,
        street=o.billing_address.street,
        zip_code=o.billing_address.zip,
        city=o.billing_address.city,
        country=o.billing_address.country,
    )


def delivery_from(o: SalesOrder) -> AddressData:
    first, last = split_name(o.customer.contact_name)
    return AddressData(
        first_name=first,
        last_name=last,
        company=o.delivery_address.company,
        street=o.delivery_address.street,
        zip_code=o.delivery_address.zip,
        city=o.delivery_address.city,
        country=o.delivery_address.country,
    )


def misc_from(o: SalesOrder) -> MiscData:
    return MiscData(
        email=o.customer.email,
        telephone=o.customer.phone,
    )


def product_from(item) -> ProductData:
    import re
    net = float(re.sub(r"[^\d.]", "", item.unit_net or "0") or 0)
    pct = float(re.sub(r"[^\d.]", "", item.vat or "0") or 0)
    return ProductData(
        item_number=item.sku,
        name=item.description,
        price_gross=f"{net * (1 + pct / 100):.2f}",
        cost_net=item.unit_net,
        quantity=item.qty,
    )


def line_from(item) -> LineItem:
    return LineItem(
        qty=item.qty,
        unit_price=item.unit_net,
        vat="",
        discount=item.discount,
    )

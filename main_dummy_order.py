import sys
sys.path.insert(0, "getOrderFromImage")
from schema import SalesOrder, Customer, Address, Payment, Item, Totals

from app_shell import FakturamaApp
from pages import OrderPage, ProductRef
from sales_adapter import debtor_from, billing_from, delivery_from, misc_from, product_from

order_data = SalesOrder(
    external_ref="WEB-2026-0714-A17",
    order_date="2026-07-14",
    customer_id="CUST-1007",
    currency="EUR",
    paid=True,
    customer=Customer(company="Northstar Office GmbH", customer_no="CUST-1007",
                      contact_name="Marta Klein", email="marta.klein@example.test",
                      phone="+49 30 5550 1420"),
    billing_address=Address(company="Northstar Office GmbH", street="Friedrichstrasse 88",
                            zip="10117", city="Berlin", country="United States"),
    delivery_address=Address(company="Northstar Office Warehouse", street="Beusselstrasse 44",
                             zip="10553", city="Berlin", country="United States"),
    payment=Payment(method="Bank Transfer", status="PAID", payment_date="2026-07-18"),
    items=[Item(sku="CHR-ERG-01", description="Ergonomic Desk Chair", qty="2", unit="pcs",
                unit_net="250.00", discount="10%", vat="19%", total_net="450.00"),
           Item(sku="MAT-DESK-02", description="Anti-Fatigue Desk Mat", qty="3", unit="pcs",
                unit_net="40.00", discount="0%", vat="19%", total_net="120.00")],
    totals=Totals(net="570.00", vat="108.30", gross="678.30"),
)

app = FakturamaApp()
order = app.create_order()
order.set_cust_ref(order_data.external_ref)

expected_debtor = debtor_from(order_data)
status, payload = order.select_debtor(expected_debtor)
if status == "NOT_FOUND":
    debtor = app.create_debtor()
    billing = billing_from(order_data)
    delivery = delivery_from(order_data)
    debtor.fill_address(billing)
    if billing != delivery:
        debtor.fill_delivery_address(delivery)
    debtor.fill_miscellaneous(misc_from(order_data))
    debtor.save()
    status, payload = order.select_debtor(expected_debtor)
if status == "CONFLICT":
    raise RuntimeError(payload)

for item in order_data.items:
    ref = ProductRef(item_no=item.sku)
    status, payload = order.select_product(ref)
    if status == "NOT_FOUND":
        product = app.create_product()
        product.fill_product(product_from(item))
        product.save()
        status, payload = order.select_product(ref)
    if status == "CONFLICT":
        raise RuntimeError(payload)

for item in order_data.items:
    order.productItems.update_quantity(item.sku, item.qty)


saved_no = order.save()

listed, source = app.documents.find_order(saved_no)

snap = order.get_value().to_dict()

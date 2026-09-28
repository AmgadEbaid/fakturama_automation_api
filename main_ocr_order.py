import sys
sys.path.insert(0, "getOrderFromImage")
from extract import extract_order, default_model

from app_shell import FakturamaApp
from pages import OrderPage, ProductRef
from sales_adapter import debtor_from, billing_from, delivery_from, misc_from, product_from

order_data = extract_order(default_model(), "orderimage/image1.png", "")

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






# Fakturama Automation

API that ingests order receipts as images into the [Fakturama](https://www.fakturama.info/) desktop app (tested against Fakturama 2.0.0), using Microsoft UIA for UI automation and a vision model combined with OCR for image extraction.

## Demo video

<video src="https://github.com/user-attachments/assets/2f737f80-3ad9-47a6-83f4-601b37865b6c" controls="controls" style="max-width: 100%;"></video>

*(2 min end-to-end run: image in, saved order out.)*

## Design

### Image data extraction

Order images come in varied, unpredictable layouts, so a fixed template parser does not work. The pipeline sends the image plus its OCR text to a vision LLM and demands schema-validated structured output back.

```python
class Item(BaseModel):
    sku: str
    qty: str = "1"
    unit_net: str = ""
    discount: str = "0%"

class SalesOrder(BaseModel):
    external_ref: str = ""
    customer: Customer = Customer()
    billing_address: Address = Address()
    items: list[Item] = Field(default_factory=list)
    totals: Totals = Totals()

order: SalesOrder = extract_order(model, "orderimage/image1.png", ocr_text)
```

Because the output is a Pydantic object, a missing or mistyped field fails fast instead of corrupting a downstream invoice.

### UI automation

Maintainable automation decouples the UI layer from business logic, so a control rename never rewrites a workflow and new screens slot in as new page classes:

```
main_*.py        business rules only (create -> attach -> verify -> save)
    |
FakturamaApp     window, toolbars, factories (create_order, ... )
    |
pages/           one class per screen, live UIA refs, no stored names
    |
ocr/             capture (screenshot) split from format (rows)
```

```python
app = FakturamaApp()
order = app.create_order()
status = order.select_debtor(expected_debtor)  # SELECTED | NOT_FOUND | CONFLICT
if status == "NOT_FOUND":
    debtor = app.create_debtor()
    debtor.fill_address(billing)
    debtor.save()
    status = order.select_debtor(expected_debtor)

for item in order_data.items:
    order.productItems.update_quantity(item.sku, item.qty)
```

Workflows branch on discrete statuses (`NOT_FOUND`, `CONFLICT`, `MISMATCH`) instead of screen scraping, so every failure arrives with its evidence attached.

## Limitations

This Fakturama build renders tables on a custom-drawn canvas that exposes no usable cell structure, and the app is table-heavy everywhere (items, debtors, documents). The workaround OCRs each table into positioned row objects used for both reading and clicking. It works, but pixel reading is inherently unreliable for serious automation and makes flows far more complex than reading real table data would.

## Included

- Creating orders, products, and debtors (address, delivery, misc sections)
- Attaching debtors/products to orders with two-check validation
- Editing order lines through the cached `productItems` model
- Reading the documents list and full order snapshots for verification

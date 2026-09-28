"""Pydantic schema (zod equivalent) for the sales order input image."""
from pydantic import BaseModel, Field


class Customer(BaseModel):
    company: str = Field(default="", description="Customer company name")
    customer_no: str = Field(default="", description="Customer account number")
    contact_name: str = Field(default="", description="Contact person full name")
    email: str = Field(default="", description="Contact email")
    phone: str = Field(default="", description="Contact phone")


class Address(BaseModel):
    company: str = ""
    street: str = ""
    zip: str = Field(default="", description="Postal code")
    city: str = ""
    country: str = ""


class Payment(BaseModel):
    method: str = ""
    status: str = Field(default="", description="e.g. PAID")
    payment_date: str = Field(default="", description="YYYY-MM-DD")


class Item(BaseModel):
    sku: str = Field(description="Item number, identity of the line")
    description: str = ""
    qty: str = "1"
    unit: str = Field(default="pcs", description="Quantity unit")
    unit_net: str = Field(default="", description="Unit net price as written")
    discount: str = "0%"
    vat: str = ""
    total_net: str = Field(default="", description="Line net total as written")


class Totals(BaseModel):
    net: str = ""
    vat: str = ""
    gross: str = ""


class SalesOrder(BaseModel):
    """Structured output of one SALES ORDER INPUT image. No pos anywhere."""
    external_ref: str = ""
    order_date: str = Field(default="", description="YYYY-MM-DD")
    customer_id: str = ""
    currency: str = "EUR"
    paid: bool = False
    customer: Customer = Customer()
    billing_address: Address = Address()
    delivery_address: Address = Address()
    payment: Payment = Payment()
    items: list[Item] = Field(default_factory=list)
    totals: Totals = Totals()

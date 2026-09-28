"""OCR package: capture (screenshot+recognize) is separate from format (rows)."""
from .capture import capture_raw, capture_preprocessed
from .format import reconstruct_table, read_table, reconstruct_product_rows, read_product_table, reconstruct_doc_rows, read_doc_table

__all__ = ["capture_raw", "capture_preprocessed", "reconstruct_table", "read_table", "reconstruct_product_rows", "read_product_table", "reconstruct_doc_rows", "read_doc_table"]

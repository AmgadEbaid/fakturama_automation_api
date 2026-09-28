"""Image + OCR -> SalesOrder via langchain structured output.

The chat model is injected so no key or vendor is hardcoded here.
Give the API key later through the model factory (env var or argument).
"""
import base64
import os
from schema import SalesOrder


def load_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def extract_order(model, image_path: str, ocr_text: str) -> SalesOrder:
    """Runs the model with structured output. Returns a SalesOrder object."""
    structured = model.with_structured_output(SalesOrder)
    message = {
        "role": "user",
        "content": [
            {"type": "text",
             "text": "Extract the sales order. Use the image first, the OCR text only "
                     "as fallback for unclear glyphs. Return numbers and dates exactly "
                     "as written. No pos field exists."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{load_image_b64(image_path)}"}},
            {"type": "text", "text": f"OCR fallback text:\n{ocr_text}"},
        ],
    }
    return structured.invoke([message])


def default_model():
    """Gemini factory. Set the key first, e.g. $env:GOOGLE_API_KEY='...'.
    Never paste the key into code or chat output.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    if not os.environ.get("GOOGLE_API_KEY"):
        raise RuntimeError("API key missing - set GOOGLE_API_KEY first")
    return ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0)


def get_order_from_image(image_path: str, ocr_text: str = "") -> SalesOrder:
    """Takes an image path, returns the SalesOrder object and logs it as JSON."""
    order = extract_order(default_model(), image_path, ocr_text)
    print(order.model_dump_json(indent=2))
    return order


if __name__ == "__main__":
    import sys
    image = sys.argv[1] if len(sys.argv) > 1 else "order.png"
    ocr = open(sys.argv[2], encoding="utf-8").read() if len(sys.argv) > 2 else ""
    get_order_from_image(image, ocr)

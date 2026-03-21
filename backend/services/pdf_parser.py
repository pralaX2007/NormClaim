"""
NormClaim — PDF Parser Service
Extracts text from PDF files using pdfplumber.
Falls back to image conversion for scanned documents.
"""

import io
import pdfplumber


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract raw text from a PDF file bytes object.
    Handles both digital PDFs (pdfplumber) and returns
    a preview string. For scanned PDFs (no text layer),
    returns an empty string so the caller can fall back
    to Gemini Vision.
    """
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def pdf_to_base64_image(file_bytes: bytes) -> str:
    """
    Convert first page of PDF to base64 PNG for Gemini Vision.
    Use when extract_text_from_pdf returns empty string (scanned doc).
    """
    import base64
    from PIL import Image

    # Convert using pdf2image if available, else use Pillow fallback
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=200)
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        # Return empty — caller will handle
        return ""

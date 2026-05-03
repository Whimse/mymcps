
import pdfplumber
from markdownify import markdownify as md

def pdf_to_markdown(pdf_path):
    # Extract text from PDF
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Optional: convert to markdown format (if input had HTML, headers, etc.)
    return md(text)

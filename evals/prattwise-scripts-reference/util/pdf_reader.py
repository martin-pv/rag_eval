import fitz
from pathlib import Path


def pdf_read_text(path: Path | str) -> str:
    with fitz.open(path) as doc:
        text = []
        for page in doc:
            page_text = page.get_text()
            text.append(page_text)
        return "\n".join(text)

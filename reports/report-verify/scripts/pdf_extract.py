from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", "", str(value).replace("\u3000", " ").replace("\xa0", " ")).strip()


def extract_pdf(path: Path) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    tables: list[list[list[str]]] = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            page_tables: list[list[list[str]]] = []
            for table in page.extract_tables():
                rows = [[clean(cell) for cell in row if clean(cell)] for row in table]
                if any(rows):
                    page_tables.append(rows)
                    tables.append(rows)
            pages.append({"number": page_number, "text": page.extract_text() or "", "tables": page_tables})
    return {
        "source": str(path),
        "text": "\n".join(page["text"] for page in pages),
        "pages": pages,
        "tables": tables,
    }


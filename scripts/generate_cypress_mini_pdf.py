#!/usr/bin/env python3
"""
Regenerate ``cypress/fixtures/mini.pdf`` using **pypdf** only.

Builds a minimal one-page PDF with a standard content stream (Helvetica + Tj)
so ingestion can extract text. Output is written via :class:`pypdf.PdfWriter`.
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cypress" / "fixtures" / "mini.pdf"

DEFAULT_PHRASE = ""


def _pdf_string_literal(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("(", r"\(")
        .replace(")", r"\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _build_minimal_pdf_bytes(phrase: str) -> bytes:
    esc = _pdf_string_literal(phrase)
    stream = f"BT /F1 18 Tf 72 720 Td ({esc}) Tj ET\n".encode("ascii")
    length = len(stream)

    chunks: list[bytes] = [b"%PDF-1.4\n"]
    offsets: list[int] = []

    def emit(part: bytes) -> None:
        offsets.append(sum(len(x) for x in chunks))
        chunks.append(part)

    emit(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    emit(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    emit(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    emit(
        f"4 0 obj\n<< /Length {length} >>\nstream\n".encode("ascii")
        + stream
        + b"endstream\nendobj\n"
    )
    emit(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    body = b"".join(chunks)
    xref_at = len(body)
    lines = ["xref", "0 6", "0000000000 65535 f "]
    for off in offsets:
        lines.append(f"{off:010d} 00000 n ")
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    return body + "\n".join(lines).encode("ascii") + trailer.encode("ascii")


def main() -> None:
    raw = _build_minimal_pdf_bytes(DEFAULT_PHRASE)
    reader = PdfReader(BytesIO(raw))
    if len(reader.pages) != 1:
        raise RuntimeError("expected one page")
    extracted = (reader.pages[0].extract_text() or "").strip()
    if not re.search(r"RAGCypress|ingestion", extracted, re.I):
        raise RuntimeError(f"unexpected extract_text from builder: {extracted!r}")

    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("wb") as f:
        writer.write(f)
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes); extract_text: {extracted!r}")


if __name__ == "__main__":
    main()

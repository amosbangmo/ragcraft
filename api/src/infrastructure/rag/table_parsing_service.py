"""
Lightweight HTML table extraction for structured reasoning (headers + rows).

Uses lxml (already a project dependency). Parsing is best-effort; callers should
fall back to raw HTML when rows/headers are empty.
"""

from __future__ import annotations

from lxml import html as lhtml


def _normalize_cell_text(cell) -> str:
    parts = [t.strip() for t in cell.itertext() if t and t.strip()]
    return " ".join(" ".join(parts).split())


def _cell_texts_for_row(tr) -> list[str]:
    return [_normalize_cell_text(c) for c in tr.xpath("./th | ./td")]


def _ordered_tr_elements(table_el) -> list:
    seen: set[int] = set()
    ordered: list = []

    def _extend(trs) -> None:
        for tr in trs:
            tid = id(tr)
            if tid not in seen:
                seen.add(tid)
                ordered.append(tr)

    _extend(table_el.xpath("./thead/tr"))
    _extend(table_el.xpath("./tbody/tr"))
    _extend(table_el.xpath("./tfoot/tr"))
    _extend(table_el.xpath("./tr"))
    return ordered


def _find_first_table_element(raw_html: str):
    raw = (raw_html or "").strip()
    if not raw:
        return None

    parser = lhtml.HTMLParser(recover=True)
    try:
        root = lhtml.fromstring(raw, parser=parser)
    except Exception:
        return None

    if root is None:
        return None

    if root.tag == "table":
        return root

    tables = root.xpath(".//table")
    return tables[0] if tables else None


class TableParsingService:
    def parse(self, raw_html: str) -> dict:
        """
        Parse the first HTML table in ``raw_html``.

        Returns:
            ``{"headers": list[str], "rows": list[list[str]]}``
            Empty lists when no table or no extractable cells.
        """
        table_el = _find_first_table_element(raw_html)
        if table_el is None:
            return {"headers": [], "rows": []}

        try:
            trs = _ordered_tr_elements(table_el)
        except Exception:
            return {"headers": [], "rows": []}

        if not trs:
            return {"headers": [], "rows": []}

        row_matrix = [_cell_texts_for_row(tr) for tr in trs]
        row_matrix = [r for r in row_matrix if r]
        if not row_matrix:
            return {"headers": [], "rows": []}

        first_tr = trs[0]
        first_has_th = bool(first_tr.xpath("./th"))

        if first_has_th:
            headers = row_matrix[0]
            body_rows = row_matrix[1:]
        elif len(row_matrix) > 1:
            headers = row_matrix[0]
            body_rows = row_matrix[1:]
        else:
            headers = []
            body_rows = row_matrix

        return {"headers": headers, "rows": body_rows}

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas


@dataclass
class PdfExportOptions:
    pagesize: Tuple[float, float] = A4
    template_id: str = "classic"  # classic|modern|institutional|boxed|compact|code_first|outline|two_column

    # Section label shown above the table/outline. "" means none.
    section_title: str = ""

    # Auto-flow to two columns on the SAME page when content would otherwise spill to next page.
    auto_two_columns: bool = True

    margin_cm: float = 1.6
    header_gap_pt: float = 12.0
    row_pad_pt: float = 4.0

    font_name: str = "Times-Roman"
    font_bold: str = "Times-Bold"
    font_italic: str = "Times-Italic"
    title_size: float = 18.0
    meta_size: float = 10.5
    section_size: float = 11.5
    max_font: float = 12.0
    min_font: float = 8.0
    leading_mult: float = 1.22


def _apply_template(opts: PdfExportOptions) -> PdfExportOptions:
    tid = (opts.template_id or "classic").strip().lower()

    # Default section title policy: keep labels clean (no "Hierarchy" by default).
    if tid == "outline":
        # Outline often benefits from a label, but only if user wants one.
        # If user leaves it blank, keep it blank.
        pass
    else:
        opts.section_title = opts.section_title or ""

    if tid in ("modern", "compact", "two_column"):
        opts.font_name = "Helvetica"
        opts.font_bold = "Helvetica-Bold"
        opts.font_italic = "Helvetica-Oblique"
        opts.title_size = 17.0
        opts.meta_size = 10.0
        opts.section_size = 11.0
        opts.leading_mult = 1.20
        opts.margin_cm = max(opts.margin_cm, 1.7)

    elif tid in ("institutional", "boxed", "classic", "code_first", "outline"):
        opts.font_name = "Times-Roman"
        opts.font_bold = "Times-Bold"
        opts.font_italic = "Times-Italic"
        opts.leading_mult = 1.22
        opts.margin_cm = max(opts.margin_cm, 1.6)
        if tid == "institutional":
            opts.title_size = 16.5
        elif tid == "boxed":
            opts.title_size = 16.5
        elif tid == "outline":
            opts.title_size = 16.0
        else:
            opts.title_size = 18.0

    return opts


def _wrap_words(text: str, font: str, size: float, max_w: float) -> List[str]:
    words = (text or "").split()
    if not words:
        return [""]

    lines: List[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if stringWidth(test, font, size) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            if stringWidth(w, font, size) > max_w:
                chunk = ""
                for ch in w:
                    t2 = chunk + ch
                    if stringWidth(t2, font, size) <= max_w:
                        chunk = t2
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = ch
                cur = chunk
            else:
                cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_paragraph(
    text: str,
    font: str,
    max_w: float,
    max_h: float,
    max_size: float,
    min_size: float,
    leading_mult: float,
) -> Tuple[float, List[str], float]:
    t = (text or "").strip()
    if not t:
        size = max_size
        leading = size * leading_mult
        return size, [""], leading

    size = max_size
    while size >= min_size:
        lines = _wrap_words(t, font, size, max_w)
        leading = size * leading_mult
        if leading * len(lines) <= max_h:
            return size, lines, leading
        size -= 0.5

    lines = _wrap_words(t, font, min_size, max_w)
    leading = min_size * leading_mult
    return min_size, lines, leading


def _draw_wrapped(
    c: Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    text: str,
    font: str,
    opts: PdfExportOptions,
    align: str = "left",
    bold: bool = False,
) -> None:
    face = opts.font_bold if bold else font
    size, lines, leading = _fit_paragraph(text, face, w, h, opts.max_font, opts.min_font, opts.leading_mult)
    c.setFont(face, size)

    y = y_top - size
    for ln in lines:
        if align == "center":
            c.drawCentredString(x + w / 2.0, y, ln)
        elif align == "right":
            c.drawRightString(x + w, y, ln)
        else:
            c.drawString(x, y, ln)
        y -= leading


def _walk_tree(nodes: List[Dict[str, Any]], level: int = 1) -> List[Tuple[int, str, str]]:
    out: List[Tuple[int, str, str]] = []
    for n in nodes:
        out.append((level, (n.get("code") or "").strip(), (n.get("name") or "").strip()))
        kids = n.get("children") or []
        out.extend(_walk_tree(kids, level + 1))
    return out


def _doc_rows(doc: Any) -> List[Tuple[int, str, str]]:
    hierarchy = getattr(doc, "hierarchy", None)
    if isinstance(hierarchy, list):
        rows = _walk_tree(hierarchy, 1)
        if rows:
            return rows
    return [(1, "", "")]


def _group_by_level1(rows: List[Tuple[int, str, str]]) -> List[List[Tuple[int, str, str]]]:
    """
    Group rows into Level-1 blocks: [ (lvl1,...), (lvl2,...), ... ] until next lvl1.
    If data doesn't start with lvl1, we treat it as one group.
    """
    groups: List[List[Tuple[int, str, str]]] = []
    cur: List[Tuple[int, str, str]] = []

    for r in rows:
        lvl = int(r[0])
        if lvl == 1:
            if cur:
                groups.append(cur)
            cur = [r]
        else:
            if not cur:
                cur = []
            cur.append(r)

    if cur:
        groups.append(cur)

    if not groups:
        return [rows]
    return groups


def export_label_pdf(doc: Any, out_path: str, opts: Optional[PdfExportOptions] = None) -> None:
    opts = _apply_template(opts or PdfExportOptions())
    tid = (opts.template_id or "classic").strip().lower()

    pagesize = opts.pagesize or A4
    c = Canvas(out_path, pagesize=pagesize)
    W, H = pagesize
    margin = opts.margin_cm * cm
    x0 = margin
    x1 = W - margin
    content_w = x1 - x0

    title = (getattr(doc, "title", "") or "").strip() or "NHMC Label"
    cab = (getattr(doc, "cabinet_section", "") or "").strip()
    rows = _doc_rows(doc)

    gap = 12.0
    indent_step = 10.0

    template_draws_own_section_title = tid in ("outline", "two_column")

    def header_footer(cont: bool = False) -> float:
        y = H - margin

        if tid == "institutional":
            c.setFont(opts.font_name, 9.0)
            c.drawString(x0, y + 10, "NHMC — Natural History Museum of Crete")
            c.drawRightString(x1, y + 10, "NHMC-Labelling")

        c.setFont(opts.font_bold, opts.title_size)
        c.drawCentredString(W / 2.0, y, title)
        y -= (opts.title_size + 6)

        if cab:
            c.setFont(opts.font_italic, opts.meta_size)
            c.drawCentredString(W / 2.0, y, f"Cabinet Section: {cab}")
            y -= (opts.meta_size + 8)
        else:
            y -= 6

        c.setLineWidth(0.8)
        c.line(x0, y, x1, y)
        y -= opts.header_gap_pt

        if tid != "boxed" and (not template_draws_own_section_title) and (opts.section_title or "").strip():
            c.setFont(opts.font_bold, opts.section_size)
            c.drawString(x0, y, (opts.section_title or "").strip() + (" (cont.)" if cont else ""))
            y -= (opts.section_size + 8)

        if tid == "institutional":
            c.setLineWidth(0.6)
            c.setFont(opts.font_name, 9.0)
            c.drawString(x0, margin - 10, "Generated by NHMC-Labelling")
            c.drawRightString(x1, margin - 10, f"Page {c.getPageNumber()}")

        return y

    def new_page() -> float:
        c.showPage()
        return header_footer(cont=True)

    y = header_footer(False)

    # ---------------- OUTLINE ----------------
    if tid == "outline":
        st = (opts.section_title or "").strip()
        if st:
            c.setFont(opts.font_bold, opts.section_size)
            c.drawString(x0, y, st)
            y -= (opts.section_size + 10)

        bullet_indent = 10.0
        line_h = 14.0

        for lvl, code, name in rows:
            if y - (line_h + 6) < margin:
                y = new_page()
                if st:
                    c.setFont(opts.font_bold, opts.section_size)
                    c.drawString(x0, y, st + " (cont.)")
                    y -= (opts.section_size + 10)

            indent = (lvl - 1) * bullet_indent
            line = f"• {code} — {name}".strip()
            _draw_wrapped(c, x0 + indent, y, content_w - indent, line_h + 10, line, opts.font_name, opts, bold=(lvl == 1))
            y -= (line_h + 6)

        c.save()
        return

    # ---------------- EXPLICIT TWO COLUMN TEMPLATE ----------------
    if tid == "two_column":
        st = (opts.section_title or "").strip()
        if st:
            c.setFont(opts.font_bold, opts.section_size)
            c.drawString(x0, y, st)
            y -= (opts.section_size + 10)

        col_gap = 18.0
        col_w = (content_w - col_gap) / 2.0

        def draw_headers(x_left: float, y_top: float) -> float:
            c.setFont(opts.font_bold, 10.0)
            c.drawString(x_left, y_top, "Code")
            c.drawString(x_left + 110, y_top, "Name")
            y2 = y_top - 10
            c.setLineWidth(0.6)
            c.line(x_left, y2, x_left + col_w, y2)
            return y2 - 10

        y = draw_headers(x0, y)
        _ = draw_headers(x0 + col_w + col_gap, y + 20)

        left_rows = rows[0::2]
        right_rows = rows[1::2]

        i = 0
        while i < max(len(left_rows), len(right_rows)):
            if y - 28 < margin:
                y = new_page()
                if st:
                    c.setFont(opts.font_bold, opts.section_size)
                    c.drawString(x0, y, st + " (cont.)")
                    y -= (opts.section_size + 10)
                y = draw_headers(x0, y)
                _ = draw_headers(x0 + col_w + col_gap, y + 20)

            if i < len(left_rows):
                lvl, code, name = left_rows[i]
                indent = (lvl - 1) * 8.0
                c.setFont(opts.font_bold if lvl == 1 else opts.font_name, 9.5)
                c.drawString(x0 + indent, y, code)
                c.setFont(opts.font_name, 9.0)
                c.drawString(x0 + 110 + indent, y, name[:60])

            if i < len(right_rows):
                lvl, code, name = right_rows[i]
                indent = (lvl - 1) * 8.0
                xR = x0 + col_w + col_gap
                c.setFont(opts.font_bold if lvl == 1 else opts.font_name, 9.5)
                c.drawString(xR + indent, y, code)
                c.setFont(opts.font_name, 9.0)
                c.drawString(xR + 110 + indent, y, name[:60])

            y -= 22
            i += 1

        c.save()
        return

    # ---------------- TABLE FAMILY (with auto 2-column flow) ----------------
    dense = (tid == "compact")
    code_first = (tid == "code_first")
    boxed = (tid == "boxed")

    row_base_h = 14.0 if dense else 18.0
    max_row_h = 72.0

    # --- boxed cabinet block ---
    if boxed:
        box_h = 46
        if y - box_h < margin:
            y = new_page()

        c.setLineWidth(0.9)
        c.roundRect(x0, y - box_h, content_w, box_h, 6, stroke=1, fill=0)
        c.setFont(opts.font_bold, 11.0)
        c.drawString(x0 + 10, y - 16, "Cabinet Section")
        c.setFont(opts.font_name, 10.0)
        c.drawString(x0 + 10, y - 32, cab or "-")
        y -= (box_h + 14)

        st = (opts.section_title or "").strip()
        if st:
            c.setFont(opts.font_bold, opts.section_size)
            c.drawString(x0, y, st)
            y -= (opts.section_size + 10)

    def row_height(code: str, name: str, code_col_w: float, name_col_w: float) -> float:
        _, code_lines, code_leading = _fit_paragraph(code, opts.font_name, code_col_w, max_row_h, opts.max_font, opts.min_font, opts.leading_mult)
        _, name_lines, name_leading = _fit_paragraph(name, opts.font_name, name_col_w, max_row_h, opts.max_font, opts.min_font, opts.leading_mult)
        needed_h = max(len(code_lines) * code_leading, len(name_lines) * name_leading, row_base_h) + opts.row_pad_pt
        return needed_h

    def draw_table_headers(x_left: float, y_top: float, col_w: float, code_col_w: float, name_col_w: float) -> float:
        c.setLineWidth(0.6)
        c.setFont(opts.font_bold, 10.5)
        c.drawString(x_left, y_top, "Code")
        c.drawString(x_left + code_col_w + gap, y_top, "Name")
        y2 = y_top - 10
        c.line(x_left, y2, x_left + col_w, y2)
        return y2 - 8

    def draw_one_row(x_left: float, y_top: float, col_w: float, code_col_w: float, name_col_w: float, lvl: int, code: str, name: str) -> float:
        indent = (lvl - 1) * indent_step
        x_code = x_left + indent
        x_name = x_left + indent + code_col_w + gap

        h = row_height(code, name, code_col_w, name_col_w)
        code_bold = (lvl == 1) or code_first

        _draw_wrapped(c, x_code, y_top, code_col_w, h, code, opts.font_name, opts, align="left", bold=code_bold)
        _draw_wrapped(c, x_name, y_top, name_col_w, h, name, opts.font_name, opts, align="left", bold=False)

        y_next = y_top - h
        c.setLineWidth(0.35 if tid in ("modern", "compact") else 0.4)
        c.line(x_left, y_next + 1.5, x_left + col_w, y_next + 1.5)
        y_next -= (4.0 if dense else 6.0)
        return y_next

    # Build Level-1 groups so we can keep them together across columns/pages.
    groups = _group_by_level1(rows)

    # Determine whether we should use 1 or 2 columns.
    # We decide by checking if everything fits in one column height.
    def total_height_for_groups(col_w: float) -> float:
        code_col_w = max(150.0, col_w * (0.34 if code_first else 0.28))
        name_col_w = col_w - code_col_w - gap

        h = 0.0
        # headers height: roughly 18
        h += 18.0
        for g in groups:
            for (lvl, code, name) in g:
                h += row_height(code, name, code_col_w, name_col_w)
                h += (4.0 if dense else 6.0)
        return h

    y_start = y
    col_height_available = y_start - margin

    use_two_cols = False
    if opts.auto_two_columns:
        # estimate one-column content height
        one_col_w = content_w
        if total_height_for_groups(one_col_w) > col_height_available:
            use_two_cols = True

    # Column geometry
    col_gap = 18.0
    if use_two_cols:
        col_w = (content_w - col_gap) / 2.0
        col_xs = [x0, x0 + col_w + col_gap]
    else:
        col_w = content_w
        col_xs = [x0]

    # Draw headers for the first column on the current page
    code_col_w = max(150.0, col_w * (0.34 if code_first else 0.28))
    name_col_w = col_w - code_col_w - gap

    col_index = 0
    x_left = col_xs[col_index]
    y = draw_table_headers(x_left, y, col_w, code_col_w, name_col_w)

    def start_new_column_or_page() -> Tuple[int, float, float]:
        nonlocal col_index, x_left, y, code_col_w, name_col_w
        if use_two_cols and col_index == 0:
            col_index = 1
            x_left = col_xs[col_index]
            # reset y to start of table area on same page
            y = y_start
            y = draw_table_headers(x_left, y, col_w, code_col_w, name_col_w)
            return col_index, x_left, y

        # new page
        y = new_page()
        y_start_local = y  # table starts at new header y
        # reset columns
        col_index = 0
        x_left = col_xs[col_index]
        y = y_start_local
        y = draw_table_headers(x_left, y, col_w, code_col_w, name_col_w)
        return col_index, x_left, y

    # Render group-by-group; never split a Level-1 group across columns if possible.
    for g in groups:
        # Compute group height in this column width
        g_h = 0.0
        for (lvl, code, name) in g:
            g_h += row_height(code, name, code_col_w, name_col_w)
            g_h += (4.0 if dense else 6.0)

        # If group doesn't fit in remaining space, move to next column/page.
        if (y - g_h) < margin:
            # If the group WOULD fit in a fresh column, move it as a block.
            fresh_y = y_start
            if (fresh_y - g_h) >= margin:
                start_new_column_or_page()
            else:
                # group too tall to fit in a fresh column:
                # we still move to next page, and if it still doesn't fit we will continue,
                # but we will REPEAT the Level-1 header row at the start of the new column/page
                # so lvl1 is never "separated".
                start_new_column_or_page()

        # Draw the group rows; if we *still* overflow mid-group (very tall group),
        # repeat lvl1 row on continuation.
        lvl1_row = None
        if g and int(g[0][0]) == 1:
            lvl1_row = g[0]

        first_row = True
        for (lvl, code, name) in g:
            h = row_height(code, name, code_col_w, name_col_w) + (4.0 if dense else 6.0)
            if (y - h) < margin:
                # continuation
                start_new_column_or_page()
                # repeat lvl1 row (if we have it) before continuing children
                if lvl1_row and not first_row:
                    y = draw_one_row(x_left, y, col_w, code_col_w, name_col_w, int(lvl1_row[0]), lvl1_row[1], lvl1_row[2])
            y = draw_one_row(x_left, y, col_w, code_col_w, name_col_w, lvl, code, name)
            first_row = False

    c.save()

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas


# ---------------- Options ----------------

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

    # typography controls
    font_regular: str = "Helvetica"
    font_bold: str = "Helvetica-Bold"
    max_font: float = 11.0
    min_font: float = 7.0
    leading_mult: float = 1.25


# ---------------- Helpers: safe normalization ----------------

def _as_str(x: Any) -> str:
    try:
        return "" if x is None else str(x)
    except Exception:
        return ""

def _norm_template_id(x: Any) -> str:
    tid = _as_str(x).strip().lower()
    if tid not in ("classic", "modern", "institutional", "boxed", "compact", "code_first", "outline", "two_column"):
        return "classic"
    return tid

def _norm_pagesize(x: Any) -> Tuple[float, float]:
    # Expect (W, H) floats in points
    if isinstance(x, (tuple, list)) and len(x) == 2:
        try:
            w = float(x[0])
            h = float(x[1])
            if w > 0 and h > 0:
                return (w, h)
        except Exception:
            pass
    return A4


# ---------------- Template defaults ----------------

def _apply_template(opts: PdfExportOptions) -> PdfExportOptions:
    tid = _norm_template_id(opts.template_id)
    opts.template_id = tid

    # Defaults per template (kept intentionally conservative).
    if tid == "classic":
        opts.font_regular = "Times-Roman"
        opts.font_bold = "Times-Bold"
        opts.max_font = 11.0
        opts.min_font = 7.0
        opts.row_pad_pt = 6.0

    elif tid == "modern":
        opts.font_regular = "Helvetica"
        opts.font_bold = "Helvetica-Bold"
        opts.max_font = 11.0
        opts.min_font = 7.0
        opts.row_pad_pt = 6.0

    elif tid == "institutional":
        opts.font_regular = "Helvetica"
        opts.font_bold = "Helvetica-Bold"
        opts.max_font = 11.0
        opts.min_font = 7.0
        opts.row_pad_pt = 6.0

    elif tid == "boxed":
        opts.font_regular = "Times-Roman"
        opts.font_bold = "Times-Bold"
        opts.max_font = 11.0
        opts.min_font = 7.0
        opts.row_pad_pt = 6.0

    elif tid == "compact":
        opts.font_regular = "Helvetica"
        opts.font_bold = "Helvetica-Bold"
        opts.max_font = 10.0
        opts.min_font = 7.0
        opts.row_pad_pt = 3.5

    elif tid == "code_first":
        opts.font_regular = "Helvetica"
        opts.font_bold = "Helvetica-Bold"
        opts.max_font = 12.0
        opts.min_font = 7.5
        opts.row_pad_pt = 5.0

    elif tid == "outline":
        opts.font_regular = "Helvetica"
        opts.font_bold = "Helvetica-Bold"
        opts.max_font = 11.0
        opts.min_font = 7.0
        opts.row_pad_pt = 4.0

    elif tid == "two_column":
        opts.font_regular = "Helvetica"
        opts.font_bold = "Helvetica-Bold"
        opts.max_font = 11.0
        opts.min_font = 7.0
        opts.row_pad_pt = 4.0

    return opts


# ---------------- Text wrapping / fitting ----------------

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


# ---------------- Tree -> rows ----------------

def _walk_tree(nodes: List[Dict[str, Any]], level: int = 1) -> List[Tuple[int, str, str]]:
    out: List[Tuple[int, str, str]] = []
    for n in nodes or []:
        out.append((level, (n.get("code") or "").strip(), (n.get("name") or "").strip()))
        kids = n.get("children") or []
        out.extend(_walk_tree(kids, level + 1))
    return out


def _doc_rows(doc: Any) -> List[Tuple[int, str, str]]:
    # The UI sets doc.hierarchy = HierarchyEditor.export_entries() (list of dicts). Keep that as source of truth.
    hierarchy = getattr(doc, "hierarchy", None)
    if isinstance(hierarchy, list):
        rows = _walk_tree(hierarchy, 1)
        if rows:
            # If the user left the default blank Level-1 node, don't force a fake row.
            if len(rows) == 1 and rows[0][1] == "" and rows[0][2] == "":
                return []
            return rows
    return []


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

    if not groups and rows:
        return [rows]
    return groups


# ---------------- Main Export ----------------

def export_label_pdf(doc: Any, out_path: str, opts: Optional[PdfExportOptions] = None) -> None:
    opts = _apply_template(opts or PdfExportOptions())

    # Hardening against bad types passed from older UI code paths
    opts.pagesize = _norm_pagesize(getattr(opts, "pagesize", A4))
    opts.template_id = _norm_template_id(getattr(opts, "template_id", "classic"))
    opts.section_title = _as_str(getattr(opts, "section_title", "")).strip()

    tid = opts.template_id

    pagesize = opts.pagesize or A4
    c = Canvas(out_path, pagesize=pagesize)
    W, H = pagesize
    margin = opts.margin_cm * cm
    x0 = margin
    x1 = W - margin
    content_w = x1 - x0

    title = (_as_str(getattr(doc, "title", "")) or "").strip() or "NHMC Label"
    cab = (_as_str(getattr(doc, "cabinet_section", "")) or "").strip()
    rows = _doc_rows(doc)

    # If nothing meaningful to export, still create a clean "header-only" PDF (no junk rows).
    gap = float(opts.header_gap_pt or 12.0)
    indent_step = 10.0

    # Determine if we ALLOW two columns:
    # - auto_two_columns must be enabled
    # - and there must be enough usable width to actually make 2 columns readable
    #   (A5 portrait gets cramped quickly).
    min_two_col_content_w = 15.0 * cm
    allow_two_cols = bool(opts.auto_two_columns) and (content_w >= min_two_col_content_w)

    # For "two_column" template we always use two columns if possible.
    if tid == "two_column":
        allow_two_cols = (content_w >= min_two_col_content_w)

    # layout region
    y = H - margin

    # ---- Header (simple + formal) ----
    c.setFont(opts.font_bold, 14)
    c.drawCentredString(W / 2.0, y - 8, title)
    y -= 24

    if cab:
        c.setFont(opts.font_regular, 10)
        c.drawCentredString(W / 2.0, y, cab)
        y -= 18

    if opts.section_title:
        c.setFont(opts.font_bold, 11)
        c.drawString(x0, y, opts.section_title)
        y -= 14
        c.line(x0, y, x1, y)
        y -= gap
    else:
        # subtle divider
        c.setLineWidth(0.8)
        c.line(x0, y, x1, y)
        y -= gap

    # Nothing else? finish.
    if not rows:
        c.save()
        return

    # ---- Column handling ----
    col_gap = 12.0
    if allow_two_cols:
        col_w = (content_w - col_gap) / 2.0
    else:
        col_w = content_w

    # columns: 0 = left, 1 = right
    col_idx = 0
    x_left = x0
    y_start = y

    def start_new_page() -> None:
        nonlocal y, col_idx, x_left, y_start
        c.showPage()
        # re-draw minimal header on new page (keeps it professional)
        y = H - margin
        c.setFont(opts.font_bold, 12)
        c.drawString(x0, y - 6, title)
        y -= 20
        if cab:
            c.setFont(opts.font_regular, 9.5)
            c.drawString(x0, y, cab)
            y -= 14
        if opts.section_title:
            c.setFont(opts.font_bold, 10.5)
            c.drawString(x0, y, opts.section_title)
            y -= 12
            c.line(x0, y, x1, y)
            y -= gap
        else:
            c.line(x0, y, x1, y)
            y -= gap

        col_idx = 0
        x_left = x0
        y_start = y

    def start_new_column_or_page() -> None:
        nonlocal col_idx, x_left, y
        if allow_two_cols and col_idx == 0:
            col_idx = 1
            x_left = x0 + col_w + col_gap
            y = y_start
            return
        start_new_page()

    # ---- Row drawing primitives ----

    def row_height(code: str, name: str, code_w: float, name_w: float) -> float:
        # estimate height using wrapping fit for the larger of code/name
        # keep this stable and not too expensive.
        # Use max_font for sizing; wrapping drives height.
        size = opts.max_font
        leading = size * opts.leading_mult
        code_lines = _wrap_words(code, opts.font_bold, size, code_w)
        name_lines = _wrap_words(name, opts.font_regular, size, name_w)
        n = max(len(code_lines), len(name_lines), 1)
        return (leading * n) + float(opts.row_pad_pt)

    def draw_one_row(x: float, y_top: float, lvl: int, code: str, name: str, code_w: float, name_w: float) -> float:
        # Indentation (outline style)
        indent = (max(lvl - 1, 0) * indent_step) if tid in ("outline", "two_column") else 0.0

        # For code_first, emphasize code.
        if tid == "code_first":
            c.setFont(opts.font_bold, 11.5)
        else:
            c.setFont(opts.font_bold, 10)

        # bullet for outline
        if tid in ("outline", "two_column"):
            c.setFont(opts.font_regular, 9.5)
            c.drawString(x + indent, y_top - 10, "•")
            text_x = x + indent + 10
        else:
            text_x = x

        # draw code + name in two "cells" (even in outline, we keep spacing)
        # tweak widths with indentation
        code_x = text_x
        name_x = text_x + code_w

        h = row_height(code, name, code_w, name_w)

        # code
        _draw_wrapped(c, code_x, y_top, code_w - 6, h, code, opts.font_bold, opts, align="left", bold=True)

        # separator for table-like templates
        if tid not in ("outline", "two_column"):
            c.setLineWidth(0.3)
            c.line(name_x - 6, y_top - h + 2, name_x - 6, y_top - 2)

        # name
        _draw_wrapped(c, name_x, y_top, name_w - 2, h, name, opts.font_regular, opts, align="left", bold=False)

        # boxed template gets subtle row boxes
        if tid == "boxed":
            c.setLineWidth(0.6)
            c.rect(x, y_top - h, (code_w + name_w), h, stroke=1, fill=0)

        return y_top - h

    # column split: choose code/name widths per template
    if tid == "code_first":
        code_col_w = col_w * 0.40
    else:
        code_col_w = col_w * 0.30
    name_col_w = col_w - code_col_w

    # In outline templates, give name more space
    if tid in ("outline", "two_column"):
        code_col_w = col_w * 0.26
        name_col_w = col_w - code_col_w

    # ---- Rendering strategy ----
    groups = _group_by_level1(rows)

    # “Two columns before next page” rule:
    # We always try right column first (if allowed), never page-break prematurely.
    dense = tid in ("compact",)

    for g in groups:
        # Estimate group height
        g_h = 0.0
        for (lvl, code, name) in g:
            g_h += row_height(code, name, code_col_w, name_col_w) + (4.0 if dense else 6.0)

        # If group doesn't fit in remaining space, move to next column/page.
        if (y - g_h) < margin:
            start_new_column_or_page()

        # Draw the group rows; if we overflow mid-group (very tall group),
        # repeat lvl1 row on continuation.
        lvl1_row = None
        if g and int(g[0][0]) == 1:
            lvl1_row = g[0]

        first_row = True
        for (lvl, code, name) in g:
            lvl_i = int(lvl)
            h = row_height(code, name, code_col_w, name_col_w) + (4.0 if dense else 6.0)
            if (y - h) < margin:
                start_new_column_or_page()
                # repeat lvl1 row when continuing children
                if lvl1_row and not first_row:
                    y = draw_one_row(x_left, y, int(lvl1_row[0]), lvl1_row[1], lvl1_row[2], code_col_w, name_col_w)
                    y -= (2.0 if dense else 4.0)
            y = draw_one_row(x_left, y, lvl_i, code, name, code_col_w, name_col_w)
            y -= (2.0 if dense else 4.0)
            first_row = False

        y -= (6.0 if dense else 10.0)

    c.save()

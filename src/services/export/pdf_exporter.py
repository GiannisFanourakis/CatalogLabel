from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

from src.app_info import APP_NAME, APP_AUTHOR, APP_URL


# ---------------- Options ----------------

@dataclass
class PdfExportOptions:
    pagesize: Tuple[float, float] = A4
    template_id: str = "classic"  # classic|modern|institutional|boxed|compact|code_first|outline|two_column
    section_title: str = ""       # "" means none
    auto_two_columns: bool = True

    margin_cm: float = 1.6
    header_gap_pt: float = 12.0
    row_pad_pt: float = 4.0

    # Typography controls (export will use these directly)
    font_regular: str = "Helvetica"
    font_bold: str = "Helvetica-Bold"
    max_font: float = 11.0
    min_font: float = 7.0
    leading_mult: float = 1.25


# ---------------- Helpers ----------------

_ALLOWED_TEMPLATES = {
    "classic",
    "modern",
    "institutional",
    "boxed",
    "compact",
    "code_first",
    "outline",
    "two_column",
}

_TEMPLATE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "classic": dict(font_regular="Times-Roman", font_bold="Times-Bold", max_font=11.0, min_font=7.0, row_pad_pt=6.0),
    "modern": dict(font_regular="Helvetica", font_bold="Helvetica-Bold", max_font=11.0, min_font=7.0, row_pad_pt=6.0),
    "institutional": dict(font_regular="Helvetica", font_bold="Helvetica-Bold", max_font=11.0, min_font=7.0, row_pad_pt=6.0),
    "boxed": dict(font_regular="Times-Roman", font_bold="Times-Bold", max_font=11.0, min_font=7.0, row_pad_pt=6.0),
    "compact": dict(font_regular="Helvetica", font_bold="Helvetica-Bold", max_font=10.0, min_font=7.0, row_pad_pt=3.5),
    "code_first": dict(font_regular="Helvetica", font_bold="Helvetica-Bold", max_font=12.0, min_font=7.5, row_pad_pt=5.0),
    "outline": dict(font_regular="Helvetica", font_bold="Helvetica-Bold", max_font=11.0, min_font=7.0, row_pad_pt=4.0),
    "two_column": dict(font_regular="Helvetica", font_bold="Helvetica-Bold", max_font=11.0, min_font=7.0, row_pad_pt=4.0),
}

def _as_str(x: Any) -> str:
    try:
        return "" if x is None else str(x)
    except Exception:
        return ""

def _norm_pagesize(ps: Any) -> Tuple[float, float]:
    try:
        if isinstance(ps, (tuple, list)) and len(ps) == 2:
            w = float(ps[0])
            h = float(ps[1])
            if w > 0 and h > 0:
                return (w, h)
    except Exception:
        pass
    return A4

def _norm_template_id(tid: Any) -> str:
    t = (_as_str(tid) or "classic").strip().lower()
    return t if t in _ALLOWED_TEMPLATES else "classic"

def _apply_template_defaults(opts: PdfExportOptions) -> PdfExportOptions:
    tid = _norm_template_id(opts.template_id)
    opts.template_id = tid
    defaults = _TEMPLATE_DEFAULTS.get(tid, {})
    for k, v in defaults.items():
        try:
            setattr(opts, k, v)
        except Exception:
            pass
    return opts

def _walk_tree(nodes: List[Dict[str, Any]], level: int = 1) -> List[Tuple[int, str, str]]:
    out: List[Tuple[int, str, str]] = []
    for n in nodes or []:
        out.append((level, (n.get("code") or "").strip(), (n.get("name") or "").strip()))
        kids = n.get("children") or []
        out.extend(_walk_tree(kids, level + 1))
    return out

def _doc_rows(doc: Any) -> List[Tuple[int, str, str]]:
    hierarchy = getattr(doc, "hierarchy", None)
    if isinstance(hierarchy, list):
        rows = _walk_tree(hierarchy, 1)
        # drop a single blank default row
        if len(rows) == 1 and rows[0][1] == "" and rows[0][2] == "":
            return []
        # drop leading blank if it exists
        if rows and rows[0][1] == "" and rows[0][2] == "":
            return rows[1:]
        return rows
    return []


# ---------------- Export ----------------

def export_label_pdf(doc: Any, out_path: str, opts: Optional[PdfExportOptions] = None) -> None:
    opts = _apply_template_defaults(opts or PdfExportOptions())

    opts.pagesize = _norm_pagesize(getattr(opts, "pagesize", A4))
    opts.template_id = _norm_template_id(getattr(opts, "template_id", "classic"))
    opts.section_title = _as_str(getattr(opts, "section_title", "")).strip()

    pagesize = opts.pagesize or A4
    c = Canvas(out_path, pagesize=pagesize)

    # PDF metadata (PDF Properties)
    try:
        c.setAuthor(APP_AUTHOR)
        c.setTitle(APP_NAME)
        c.setSubject("Catalog labeling and hierarchy export")
        c.setCreator(f"{APP_NAME} ({APP_URL})")
    except Exception:
        pass

    W, H = pagesize
    margin = float(opts.margin_cm) * cm
    x0 = margin
    x1 = W - margin
    content_w = x1 - x0

    title = (_as_str(getattr(doc, "title", "")) or "").strip() or APP_NAME
    cab = (_as_str(getattr(doc, "cabinet_section", "")) or "").strip()
    rows = _doc_rows(doc)

    # --- Header ---
    y = H - margin
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

    c.setLineWidth(0.8)
    c.line(x0, y, x1, y)
    y -= float(opts.header_gap_pt)

    if not rows:
        c.save()
        return

    # --- Two-column decision ---
    min_two_col_w = 15.0 * cm
    allow_two_cols = bool(opts.auto_two_columns) and (content_w >= min_two_col_w)
    if opts.template_id == "two_column":
        allow_two_cols = (content_w >= min_two_col_w)

    col_gap = 12.0
    col_w = (content_w - col_gap) / 2.0 if allow_two_cols else content_w

    # columns bookkeeping
    col_idx = 0
    x_left = x0
    y_start = y

    def start_new_page() -> None:
        nonlocal y, col_idx, x_left, y_start
        c.showPage()

        # re-apply metadata is optional; ReportLab keeps it, but harmless
        try:
            c.setAuthor(APP_AUTHOR)
            c.setTitle(APP_NAME)
        except Exception:
            pass

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

        c.setLineWidth(0.8)
        c.line(x0, y, x1, y)
        y -= float(opts.header_gap_pt)

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

    # --- Render rows ---
    base_size = float(opts.max_font)
    leading = base_size * float(opts.leading_mult)

    # widths by template
    if opts.template_id == "code_first":
        code_col_w = col_w * 0.40
    else:
        code_col_w = col_w * 0.30
    name_col_w = col_w - code_col_w

    if opts.template_id in ("outline", "two_column"):
        code_col_w = col_w * 0.26
        name_col_w = col_w - code_col_w

    def draw_row(lvl: int, code: str, name: str) -> None:
        nonlocal y
        tid = opts.template_id

        indent_step = 10.0
        indent = (max(lvl - 1, 0) * indent_step) if tid in ("outline", "two_column") else 0.0
        bullet_gap = 10.0

        x = x_left + indent
        if tid in ("outline", "two_column"):
            c.setFont(opts.font_regular, base_size)
            c.drawString(x, y, "•")
            x = x + bullet_gap

        # code
        c.setFont(opts.font_bold, base_size + (1.5 if tid == "code_first" else 0.0))
        c.drawString(x, y, code)

        # name
        c.setFont(opts.font_regular, base_size)
        c.drawString(x + code_col_w, y, name)

        y -= (leading + float(opts.row_pad_pt))

    for (lvl, code, name) in rows:
        if (y - (leading + float(opts.row_pad_pt))) < margin:
            start_new_column_or_page()
        draw_row(int(lvl), code, name)

    c.save()

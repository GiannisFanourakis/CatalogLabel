from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from src.app_info import APP_NAME, APP_AUTHOR, APP_URL
from src.services.export.pdf.template_specs import (
    merged_template_defaults,
    norm_template_id,
    INDENT_STEP_PT,
    BULLET_GAP_PT,
)


# ---------------- Options ----------------

@dataclass
class PdfExportOptions:
    pagesize: Tuple[float, float] = A4
    template_id: str = "classic"
    section_title: str = ""
    auto_two_columns: bool = True

    margin_cm: float = 1.6
    header_gap_pt: float = 12.0
    row_pad_pt: float = 4.0

    font_regular: str = "Helvetica"
    font_bold: str = "Helvetica-Bold"
    max_font: float = 11.0
    min_font: float = 7.0
    leading_mult: float = 1.25

    max_name_lines: int = 3
    code_name_gap_pt: float = 10.0

    header_title_size: float = 14.0
    header_sub_size: float = 10.0
    header_section_size: float = 11.0
    header_rule_width: float = 0.8

    row_rules: bool = False
    row_rule_width: float = 0.35
    row_rule_every: int = 1


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


def _apply_template_defaults(opts: PdfExportOptions) -> PdfExportOptions:
    tid = norm_template_id(opts.template_id)
    opts.template_id = tid
    defaults = merged_template_defaults(tid)
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
        if rows and rows[0][1] == "" and rows[0][2] == "":
            return rows[1:]
        return rows
    return []


def _wrap_text(text: str, font_name: str, font_size: float, max_width: float) -> List[str]:
    t = (text or "").strip()
    if not t:
        return [""]

    words = t.split()
    lines: List[str] = []
    cur: List[str] = []

    def width(parts: List[str]) -> float:
        s = " ".join(parts).strip()
        return stringWidth(s, font_name, font_size)

    for w in words:
        if not cur:
            cur = [w]
            continue
        trial = cur + [w]
        if width(trial) <= max_width:
            cur = trial
        else:
            lines.append(" ".join(cur))
            cur = [w]

    if cur:
        lines.append(" ".join(cur))

    fixed: List[str] = []
    for line in lines:
        if stringWidth(line, font_name, font_size) <= max_width:
            fixed.append(line)
            continue

        buf = ""
        for ch in line:
            trial = buf + ch
            if stringWidth(trial, font_name, font_size) <= max_width:
                buf = trial
            else:
                if buf:
                    fixed.append(buf)
                buf = ch
        if buf:
            fixed.append(buf)

    return fixed if fixed else [""]


def _ellipsis_fit(text: str, font_name: str, font_size: float, max_width: float) -> str:
    s = (text or "").strip()
    if stringWidth(s, font_name, font_size) <= max_width:
        return s

    ell = "…"
    if stringWidth(ell, font_name, font_size) > max_width:
        return ""

    lo, hi = 0, len(s)
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = s[:mid].rstrip() + ell
        if stringWidth(cand, font_name, font_size) <= max_width:
            best = cand
            lo = mid + 1
        else:
            hi = mid - 1
    return best or ell


def export_label_pdf(doc: Any, out_path: str, opts: Optional[PdfExportOptions] = None) -> None:
    opts = _apply_template_defaults(opts or PdfExportOptions())

    opts.pagesize = _norm_pagesize(getattr(opts, "pagesize", A4))
    opts.template_id = norm_template_id(getattr(opts, "template_id", "classic"))
    opts.section_title = _as_str(getattr(opts, "section_title", "")).strip()

    pagesize = opts.pagesize or A4
    c = Canvas(out_path, pagesize=pagesize)

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

    # Header
    y = H - margin

    c.setFont(opts.font_bold, float(opts.header_title_size))
    c.drawCentredString(W / 2.0, y - 8, title)
    y -= 24

    if cab:
        c.setFont(opts.font_regular, float(opts.header_sub_size))
        c.drawCentredString(W / 2.0, y, cab)
        y -= 18

    if opts.section_title:
        c.setFont(opts.font_bold, float(opts.header_section_size))
        c.drawString(x0, y, opts.section_title)
        y -= 14

    c.setLineWidth(float(opts.header_rule_width))
    c.line(x0, y, x1, y)
    y -= float(opts.header_gap_pt)

    if not rows:
        c.save()
        return

    # Two-column decision
    min_two_col_w = 15.0 * cm
    can_two_cols = (content_w >= min_two_col_w)
    allow_two_cols = bool(opts.auto_two_columns) and can_two_cols
    if opts.template_id == "two_column":
        allow_two_cols = can_two_cols

    base_size = float(opts.max_font)
    leading = base_size * float(opts.leading_mult)
    avail_h = max(0.0, y - margin)
    est_h = len(rows) * (leading + float(opts.row_pad_pt))
    if bool(opts.auto_two_columns) and can_two_cols and est_h > (avail_h * 1.10):
        allow_two_cols = True

    col_gap = 12.0
    col_w = (content_w - col_gap) / 2.0 if allow_two_cols else content_w

    col_idx = 0
    x_left = x0
    y_start = y

    def _draw_page_header() -> None:
        nonlocal y, y_start, col_idx, x_left
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

        c.setLineWidth(float(opts.header_rule_width))
        c.line(x0, y, x1, y)
        y -= float(opts.header_gap_pt)

        col_idx = 0
        x_left = x0
        y_start = y

    def start_new_page() -> None:
        c.showPage()
        try:
            c.setAuthor(APP_AUTHOR)
            c.setTitle(APP_NAME)
        except Exception:
            pass
        _draw_page_header()

    def start_new_column_or_page() -> None:
        nonlocal col_idx, x_left, y
        if allow_two_cols and col_idx == 0:
            col_idx = 1
            x_left = x0 + col_w + col_gap
            y = y_start
            return
        start_new_page()

    # Column widths
    if opts.template_id == "code_first":
        code_col_w = col_w * 0.40
    else:
        code_col_w = col_w * 0.30

    if opts.template_id in ("outline", "two_column"):
        code_col_w = col_w * 0.26

    code_name_gap = max(0.0, float(getattr(opts, "code_name_gap_pt", 10.0)))
    name_col_w = max(30.0, col_w - code_col_w - code_name_gap)

    row_rule_on = bool(getattr(opts, "row_rules", False))
    row_rule_w = float(getattr(opts, "row_rule_width", 0.35))
    row_rule_every = max(1, int(getattr(opts, "row_rule_every", 1)))

    def measure_row_height(tid: str, lvl: int, name: str) -> Tuple[float, List[str], float]:
        indent = (max(lvl - 1, 0) * INDENT_STEP_PT) if tid in ("outline", "two_column") else 0.0
        avail = max(30.0, name_col_w - indent)
        lines = _wrap_text(name, opts.font_regular, base_size, avail)
        if opts.max_name_lines and len(lines) > int(opts.max_name_lines):
            lines = lines[: int(opts.max_name_lines)]
            lines[-1] = _ellipsis_fit(lines[-1], opts.font_regular, base_size, avail)

        h = (len(lines) * leading) + float(opts.row_pad_pt)
        return h, lines, indent

    def draw_row(idx: int, lvl: int, code: str, name: str) -> None:
        nonlocal y
        tid = opts.template_id
        row_h, name_lines, indent = measure_row_height(tid, lvl, name)
        if y - row_h < margin:
            start_new_column_or_page()

        x = x_left + indent

        if tid in ("outline", "two_column"):
            c.setFont(opts.font_regular, base_size)
            c.drawString(x, y, "•")
            x = x + BULLET_GAP_PT

        c.setFont(opts.font_bold, base_size + (1.5 if tid == "code_first" else 0.0))
        c.drawString(x, y, code)

        c.setFont(opts.font_regular, base_size)
        name_x = x + code_col_w + code_name_gap
        yy = y
        for line in name_lines:
            c.drawString(name_x, yy, line)
            yy -= leading

        y -= row_h

        if row_rule_on and (idx % row_rule_every == 0):
            c.saveState()
            c.setLineWidth(row_rule_w)
            c.line(x_left, y + 1.5, x_left + col_w, y + 1.5)
            c.restoreState()

    for i, (lvl, code, name) in enumerate(rows, start=1):
        draw_row(i, int(lvl or 1), _as_str(code), _as_str(name))

    c.save()

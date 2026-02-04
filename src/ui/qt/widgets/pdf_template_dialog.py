from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QPainter, QPixmap, QPen, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
    QWidget,
    QComboBox,
    QLineEdit,
    QSizePolicy,
)

from src.domain.models import LabelDocument
from src.services.export.pdf.template_specs import (
    merged_template_defaults,
    norm_template_id,
    INDENT_STEP_PT,
    BULLET_GAP_PT,
)


@dataclass(frozen=True)
class TemplateChoice:
    template_id: str
    template_name: str


TEMPLATES = [
    TemplateChoice("classic", "Classic Formal (Serif)"),
    TemplateChoice("modern", "Modern Formal (Sans)"),
    TemplateChoice("institutional", "Institutional (Header + Footer)"),
    TemplateChoice("boxed", "Boxed Sections (Formal Blocks)"),
    TemplateChoice("compact", "Compact Card (Dense Layout)"),
    TemplateChoice("code_first", "Code-First (Large Codes)"),
    TemplateChoice("outline", "Indented Outline (No Table)"),
    TemplateChoice("two_column", "Two-Column Hierarchy"),
]


class PdfTemplateDialog(QDialog):
    """
    Preview is QPainter-based but now uses robust QRect text drawing so we don't
    get baseline clipping artifacts (like the dreaded single-letter 'C').
    Layout constants are still shared with exporter via template_specs.
    """

    SECTION_PRESETS = [
        ("", "(None)"),
        ("Classification", "Classification"),
        ("Taxonomy", "Taxonomy"),
        ("Collection Path", "Collection Path"),
        ("Hierarchy", "Hierarchy"),
        ("__custom__", "Custom…"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose PDF Template")
        self.setModal(True)
        self.setMinimumWidth(920)

        self._selected_template_id = "classic"
        self._title = "NHMC Label"
        self._cabinet = "Cabinet Section: Example Cabinet A"
        self._preview_doc: Optional[LabelDocument] = None

        self._build_ui()
        self._wire()
        self._update_preview()

    # ---------- public API ----------
    def set_sample_content(self, title: str, cabinet: str) -> None:
        if (title or "").strip():
            self._title = title.strip()
        if (cabinet or "").strip():
            self._cabinet = cabinet.strip()
        self._update_preview()

    def set_preview_document(self, doc: LabelDocument) -> None:
        self._preview_doc = doc
        t = (getattr(doc, "title", "") or "").strip()
        c = (getattr(doc, "cabinet_section", "") or "").strip()
        if t:
            self._title = t
        if c:
            self._cabinet = c
        self._update_preview()

    def selected_template_id(self) -> str:
        return self._selected_template_id

    def selected_section_title(self) -> str:
        if self.cbo_section.currentData() == "__custom__":
            return (self.ed_custom.text() or "").strip()
        val = self.cbo_section.currentData()
        return (val or "").strip()

    def set_selected_section_title(self, title: str) -> None:
        t = (title or "").strip()

        for i in range(self.cbo_section.count()):
            if (self.cbo_section.itemData(i) or "") == t:
                self.cbo_section.setCurrentIndex(i)
                self.ed_custom.setText("")
                self._on_section_changed()
                return

        if t == "":
            for i in range(self.cbo_section.count()):
                if (self.cbo_section.itemData(i) or "") == "":
                    self.cbo_section.setCurrentIndex(i)
                    self.ed_custom.setText("")
                    self._on_section_changed()
                    return

        for i in range(self.cbo_section.count()):
            if (self.cbo_section.itemData(i) or "") == "__custom__":
                self.cbo_section.setCurrentIndex(i)
                self.ed_custom.setText(t)
                self._on_section_changed()
                return

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        help_txt = QLabel(
            "Pick a presentation style for the exported label PDF.\n"
            "Preview uses the same layout rules as export (wrapping, indentation, gutters)."
        )
        help_txt.setWordWrap(True)
        root.addWidget(help_txt)

        sec_row = QHBoxLayout()
        sec_row.setSpacing(8)

        sec_row.addWidget(QLabel("Section Title:"), 0)

        self.cbo_section = QComboBox()
        self.cbo_section.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.cbo_section.setMinimumWidth(220)
        for val, label in self.SECTION_PRESETS:
            self.cbo_section.addItem(label, userData=val)
        self.cbo_section.setCurrentIndex(0)
        sec_row.addWidget(self.cbo_section, 0)

        self.ed_custom = QLineEdit()
        self.ed_custom.setPlaceholderText("Type custom section title…")
        self.ed_custom.setEnabled(False)
        self.ed_custom.setMinimumWidth(260)
        sec_row.addWidget(self.ed_custom, 0)

        sec_row.addStretch(1)
        root.addLayout(sec_row)

        mid = QHBoxLayout()
        mid.setSpacing(12)
        root.addLayout(mid, 1)

        box = QGroupBox("Templates")
        left = QVBoxLayout(box)
        left.setContentsMargins(10, 10, 10, 10)
        left.setSpacing(8)

        self.grp = QButtonGroup(self)
        self.radios = {}

        for i, t in enumerate(TEMPLATES):
            rb = QRadioButton(t.template_name)
            self.grp.addButton(rb, i)
            self.radios[t.template_id] = rb
            left.addWidget(rb)

        self.radios["classic"].setChecked(True)
        left.addStretch(1)
        mid.addWidget(box, 0)

        prev_box = QGroupBox("Preview")
        prev_lay = QVBoxLayout(prev_box)
        prev_lay.setContentsMargins(10, 10, 10, 10)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(QSize(600, 740))
        self.preview.setStyleSheet("background: #111; border: 1px solid #333;")
        prev_lay.addWidget(self.preview, 1)

        mid.addWidget(prev_box, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_ok = QPushButton("Use Selected Template")
        self.btn_ok.setDefault(True)

        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)
        root.addLayout(btns)

    def _wire(self) -> None:
        self.grp.buttonClicked.connect(self._on_template_changed)
        self.cbo_section.currentIndexChanged.connect(self._on_section_changed)
        self.ed_custom.textChanged.connect(lambda _t: self._update_preview())
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)

    def _on_template_changed(self) -> None:
        for tid, rb in self.radios.items():
            if rb.isChecked():
                self._selected_template_id = tid
                break
        self._update_preview()

    def _on_section_changed(self) -> None:
        is_custom = (self.cbo_section.currentData() == "__custom__")
        self.ed_custom.setEnabled(is_custom)
        if not is_custom:
            self.ed_custom.setText("")
        self._update_preview()

    # -------- preview helpers --------
    def _qt_family_from_export_font(self, export_font: str) -> str:
        f = (export_font or "").lower()
        if "times" in f:
            return "Times New Roman"
        return "Segoe UI"

    def _walk_tree(self, nodes: List[Dict[str, Any]], level: int = 1) -> List[Tuple[int, str, str]]:
        out: List[Tuple[int, str, str]] = []
        for n in nodes or []:
            out.append((level, (n.get("code") or "").strip(), (n.get("name") or "").strip()))
            kids = n.get("children") or []
            out.extend(self._walk_tree(kids, level + 1))
        return out

    def _doc_rows(self) -> List[Tuple[int, str, str]]:
        if self._preview_doc and isinstance(getattr(self._preview_doc, "hierarchy", None), list):
            rows = self._walk_tree(self._preview_doc.hierarchy, 1)  # type: ignore[arg-type]
            if rows and rows[0][1] == "" and rows[0][2] == "":
                return rows[1:]
            return rows
        return [
            (1, "01", "Mammals"),
            (2, "01.1", "Mammals – Carnivora"),
            (3, "01.1.1", "Katsoulia"),
            (1, "02", "Birds"),
            (2, "02.1", "Birds – Passerines"),
            (3, "02.1.1", "Ornithes"),
            (1, "03", "Reptiles"),
            (2, "03.1", "Reptiles – Lizards"),
            (3, "03.1.1", "Liakonia"),
        ]

    def _wrap_lines(self, fm: QFontMetrics, text: str, max_w: int) -> List[str]:
        t = (text or "").strip()
        if not t:
            return [""]

        words = t.split()
        lines: List[str] = []
        cur: List[str] = []

        def width(s: str) -> int:
            return fm.horizontalAdvance(s)

        for w in words:
            if not cur:
                cur = [w]
                continue
            trial = " ".join(cur + [w])
            if width(trial) <= max_w:
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]

        if cur:
            lines.append(" ".join(cur))

        fixed: List[str] = []
        for line in lines:
            if width(line) <= max_w:
                fixed.append(line)
                continue
            buf = ""
            for ch in line:
                trial = buf + ch
                if width(trial) <= max_w:
                    buf = trial
                else:
                    if buf:
                        fixed.append(buf)
                    buf = ch
            if buf:
                fixed.append(buf)

        return fixed if fixed else [""]

    def _ellipsis_fit(self, fm: QFontMetrics, text: str, max_w: int) -> str:
        s = (text or "").strip()
        if fm.horizontalAdvance(s) <= max_w:
            return s
        ell = "…"
        if fm.horizontalAdvance(ell) > max_w:
            return ""
        lo, hi = 0, len(s)
        best = ell
        while lo <= hi:
            mid = (lo + hi) // 2
            cand = s[:mid].rstrip() + ell
            if fm.horizontalAdvance(cand) <= max_w:
                best = cand
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    # ---------------- Preview rendering ----------------
    def _update_preview(self) -> None:
        pm = QPixmap(600, 740)
        pm.fill(Qt.black)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)

        # paper
        paper_x, paper_y = 80, 45
        paper_w, paper_h = 440, 650
        p.setPen(QPen(Qt.white, 2))
        p.setBrush(Qt.white)
        p.drawRoundedRect(paper_x, paper_y, paper_w, paper_h, 10, 10)

        tid = norm_template_id(self._selected_template_id)
        spec = merged_template_defaults(tid)
        section_title = self.selected_section_title()
        rows = self._doc_rows()

        fam = self._qt_family_from_export_font(spec.get("font_regular", "Helvetica"))

        title_font = QFont(fam, int(round(float(spec.get("header_title_size", 14.0)))), QFont.Bold)
        sub_font = QFont(fam, int(round(float(spec.get("header_sub_size", 10.0)))))
        section_font = QFont(fam, int(round(float(spec.get("header_section_size", 11.0)))), QFont.Bold)

        base_size = float(spec.get("max_font", 11.0))
        leading_mult = float(spec.get("leading_mult", 1.25))
        body_font = QFont(fam, int(round(base_size)))
        body_b = QFont(fam, int(round(base_size)), QFont.Bold)

        left = paper_x + 22
        right = paper_x + paper_w - 22
        y = paper_y + 20

        def draw_text_rect(font: QFont, x: int, y_top: int, w: int, h: int, text: str, flags: Qt.AlignmentFlag) -> None:
            p.setFont(font)
            p.setPen(Qt.black)
            p.drawText(QRect(x, y_top, w, h), int(flags), text)

        # institutional small header line
        if tid == "institutional":
            draw_text_rect(QFont(fam, 8), left, y - 4, right - left, 14, "NHMC — Natural History Museum of Crete", Qt.AlignLeft | Qt.AlignTop)
            y += 10

        # main title centered
        draw_text_rect(title_font, paper_x, y, paper_w, 28, (self._title or "").strip()[:72], Qt.AlignHCenter | Qt.AlignTop)
        y += 26

        # cabinet centered
        draw_text_rect(sub_font, paper_x, y, paper_w, 20, (self._cabinet or "").strip()[:90], Qt.AlignHCenter | Qt.AlignTop)
        y += 18

        # section title
        if section_title:
            draw_text_rect(section_font, left, y, right - left, 18, section_title, Qt.AlignLeft | Qt.AlignTop)
            y += 18

        # header rule
        p.setPen(QPen(Qt.black, max(1, int(round(float(spec.get("header_rule_width", 1.0)))))))
        p.drawLine(left, y + 6, right, y + 6)
        y += int(round(float(spec.get("header_gap_pt", 12.0))))

        # two-column heuristic for preview only
        allow_two_cols = (tid == "two_column") or (len(rows) >= 18 and tid in ("outline", "modern", "compact"))
        col_gap = 14
        col_w = ((right - left) - col_gap) // 2 if allow_two_cols else (right - left)

        x_left = left
        y_start = y
        col_idx = 0

        # column widths by template
        if tid == "code_first":
            code_col_w = int(col_w * 0.40)
        else:
            code_col_w = int(col_w * 0.30)
        if tid in ("outline", "two_column"):
            code_col_w = int(col_w * 0.26)

        code_name_gap = int(round(float(spec.get("code_name_gap_pt", 10.0))))
        name_col_w = max(80, col_w - code_col_w - code_name_gap)

        row_rules = bool(spec.get("row_rules", False))
        row_rule_every = max(1, int(spec.get("row_rule_every", 1)))

        fm = QFontMetrics(body_font)
        lead_px = max(12, int(round(fm.height() * (leading_mult / 1.25))))  # stable-ish
        pad_px = max(2, int(round(float(spec.get("row_pad_pt", 4.0)))))

        def next_col_or_stop() -> None:
            nonlocal col_idx, x_left, y
            if allow_two_cols and col_idx == 0:
                col_idx = 1
                x_left = left + col_w + col_gap
                y = y_start
                return
            y = paper_y + paper_h - 20  # stop drawing

        # draw rows (top-aligned rectangles, no baseline bugs)
        for idx, (lvl, code, name) in enumerate(rows, start=1):
            lvl_i = int(lvl or 1)
            indent = int(round((max(lvl_i - 1, 0) * INDENT_STEP_PT))) if tid in ("outline", "two_column") else 0

            # wrap name
            avail_name_w = max(60, name_col_w - indent)
            lines = self._wrap_lines(fm, name, avail_name_w)
            max_lines = int(spec.get("max_name_lines", 3) or 3)
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines[-1] = self._ellipsis_fit(fm, lines[-1], avail_name_w)

            row_h = (len(lines) * lead_px) + pad_px

            if y + row_h > (paper_y + paper_h - 24):
                next_col_or_stop()

            x = x_left + indent

            # bullet
            if tid in ("outline", "two_column"):
                draw_text_rect(body_font, x, y, 14, lead_px, "•", Qt.AlignLeft | Qt.AlignTop)
                x += int(round(BULLET_GAP_PT))

            # code
            draw_text_rect(body_b, x, y, code_col_w, lead_px, str(code), Qt.AlignLeft | Qt.AlignTop)

            # name lines
            name_x = x + code_col_w + code_name_gap
            yy = y
            for line in lines:
                draw_text_rect(body_font, name_x, yy, avail_name_w, lead_px, line, Qt.AlignLeft | Qt.AlignTop)
                yy += lead_px

            y += row_h

            # row rules BELOW the row (never through text)
            if row_rules and (idx % row_rule_every == 0):
                p.setPen(QPen(Qt.black, 1))
                p.drawLine(x_left, y - 2, x_left + col_w, y - 2)
                p.setPen(Qt.black)

        p.end()
        self.preview.setPixmap(pm)

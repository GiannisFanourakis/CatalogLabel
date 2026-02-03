from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QPixmap, QPen, QFont
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
    Template chooser with fast mock preview (QPainter).
    Includes Section Title selector used by the real PDF exporter.
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

        # section title ("" means none)
        self._section_title: str = ""

        # sample hierarchy used in preview
        self._rows = [
            ("01", "Mammals"),
            ("01.1", "Mammals – Carnivora"),
            ("01.2", "Mammals – Herbivora"),
            ("02", "Birds"),
            ("02.1", "Birds – Passerines"),
        ]

        self._build_ui()
        self._wire()
        self._update_preview()

    # ---------- public API ----------
    def set_sample_content(self, title: str, cabinet: str) -> None:
        self._title = title or self._title
        self._cabinet = cabinet or self._cabinet
        self._update_preview()

    def selected_template_id(self) -> str:
        return self._selected_template_id

    def selected_section_title(self) -> str:
        # "" = none
        if self.cbo_section.currentData() == "__custom__":
            return (self.ed_custom.text() or "").strip()
        val = self.cbo_section.currentData()
        return (val or "").strip()

    def set_selected_section_title(self, title: str) -> None:
        """
        Restore a previous selection.
        If it doesn't match a preset, we set Custom and fill it.
        """
        t = (title or "").strip()
        # exact preset?
        for i in range(self.cbo_section.count()):
            if (self.cbo_section.itemData(i) or "") == t:
                self.cbo_section.setCurrentIndex(i)
                self.ed_custom.setText("")
                self._on_section_changed()
                return

        if t == "":
            # none
            for i in range(self.cbo_section.count()):
                if (self.cbo_section.itemData(i) or "") == "":
                    self.cbo_section.setCurrentIndex(i)
                    self.ed_custom.setText("")
                    self._on_section_changed()
                    return

        # custom
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
            "Use 'Section Title' if you want an extra heading above the hierarchy (most labels don't need it)."
        )
        help_txt.setWordWrap(True)
        root.addWidget(help_txt)

        # Section title controls
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

        # left template list
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

        # preview
        prev_box = QGroupBox("Preview")
        prev_lay = QVBoxLayout(prev_box)
        prev_lay.setContentsMargins(10, 10, 10, 10)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(QSize(600, 740))
        self.preview.setStyleSheet("background: #111; border: 1px solid #333;")
        prev_lay.addWidget(self.preview, 1)

        mid.addWidget(prev_box, 1)

        # buttons
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

        tid = (self._selected_template_id or "classic").strip().lower()
        section_title = self.selected_section_title()

        # fonts
        fam = "Segoe UI" if tid in ("modern", "compact", "two_column") else "Times New Roman"
        title_font = QFont(fam, 15, QFont.Bold, False)
        meta_font_ital = QFont(fam, 9, QFont.Normal, True)
        meta_font = QFont(fam, 9, QFont.Normal, False)
        body = QFont(fam, 9, QFont.Normal, False)
        body_b = QFont(fam, 9, QFont.Bold, False)

        left = paper_x + 22
        right = paper_x + paper_w - 22
        y = paper_y + 22

        p.setPen(Qt.black)

        if tid == "institutional":
            p.setFont(QFont(fam, 8, QFont.Normal, False))
            p.drawText(left, y - 8, right - left, 14, Qt.AlignLeft | Qt.AlignVCenter, "NHMC — Natural History Museum of Crete")

        p.setFont(title_font)
        p.drawText(paper_x, y, paper_w, 26, Qt.AlignHCenter | Qt.AlignVCenter, (self._title or "")[:42])
        y += 28

        p.setFont(meta_font_ital if tid in ("classic", "boxed", "institutional") else meta_font)
        p.drawText(paper_x, y, paper_w, 18, Qt.AlignHCenter | Qt.AlignVCenter, (self._cabinet or "")[:54])
        y += 18

        if tid != "boxed":
            p.setPen(QPen(Qt.black, 1))
            p.drawLine(left, y + 10, right, y + 10)
            y += 26

        # Helpers
        def draw_section_title(y0: int, default_label: str) -> int:
            nonlocal section_title
            if (section_title or "").strip():
                label = section_title.strip()
            else:
                label = default_label

            # If user chose none, do nothing.
            if label.strip() == "":
                return y0

            p.setFont(QFont(body.family(), 10, QFont.Bold, False))
            p.drawText(left, y0, right - left, 18, Qt.AlignLeft | Qt.AlignVCenter, label)
            return y0 + 20

        def draw_table(y0: int, code_scale: float = 1.0, dense: bool = False, boxed: bool = False) -> int:
            y = y0
            if boxed:
                # cabinet block
                p.setPen(QPen(Qt.black, 1))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(left - 6, y - 10, (right - left) + 12, 70, 6, 6)
                p.setFont(body_b)
                p.drawText(left, y, right - left, 16, Qt.AlignLeft | Qt.AlignVCenter, "Cabinet Section")
                p.setFont(body)
                p.drawText(left, y + 16, right - left, 16, Qt.AlignLeft | Qt.AlignVCenter, (self._cabinet or "")[:60])
                y += 80

                y = draw_section_title(y, "")  # boxed doesn't need default
                # table box
                p.drawRoundedRect(left - 6, y - 10, (right - left) + 12, 240, 6, 6)
                y += 8
            else:
                # table-family: section title optional, default none
                y = draw_section_title(y, "")

            # column headers
            p.setFont(body_b)
            p.drawText(left, y, 140, 16, Qt.AlignLeft | Qt.AlignVCenter, "Code")
            p.drawText(left + 160, y, right - (left + 160), 16, Qt.AlignLeft | Qt.AlignVCenter, "Name")
            y += 14
            p.setPen(QPen(Qt.black, 1))
            p.drawLine(left, y + 4, right, y + 4)
            y += 12
            p.setPen(Qt.black)

            row_h = 18 if not dense else 14
            for code, name in self._rows[:5]:
                cfont = QFont(body.family(), int(9 * code_scale), QFont.Bold if code_scale > 1.0 else QFont.Normal, False)
                p.setFont(cfont)
                p.drawText(left, y, 150, row_h, Qt.AlignLeft | Qt.AlignVCenter, code)

                p.setFont(body)
                p.drawText(left + 160, y, right - (left + 160), row_h, Qt.AlignLeft | Qt.AlignVCenter, name)
                y += row_h
                p.setPen(QPen(Qt.black, 1))
                p.drawLine(left, y + 2, right, y + 2)
                p.setPen(Qt.black)
                y += (6 if not dense else 4)

            return y

        def draw_outline(y0: int) -> int:
            y = y0
            # outline: default title is "Classification (Outline)" unless user set none/custom
            y = draw_section_title(y, "Classification (Outline)")
            y += 4

            p.setFont(body)
            for code, name in self._rows[:5]:
                indent = 0
                if "." in code:
                    indent = 14
                if code.count(".") >= 2:
                    indent = 28
                line = f"• {code}  —  {name}"
                p.drawText(left + indent, y, right - left - indent, 16, Qt.AlignLeft | Qt.AlignVCenter, line)
                y += 18
            return y

        def draw_two_column(y0: int) -> int:
            y = y0
            y = draw_section_title(y, "")  # default none
            y += 2

            col_mid = left + (right - left) / 2.0
            p.setFont(body_b)
            p.drawText(left, y, 140, 16, Qt.AlignLeft | Qt.AlignVCenter, "Code")
            p.drawText(left + 110, y, col_mid - (left + 110), 16, Qt.AlignLeft | Qt.AlignVCenter, "Name")
            p.drawText(col_mid + 10, y, 140, 16, Qt.AlignLeft | Qt.AlignVCenter, "Code")
            p.drawText(col_mid + 120, y, right - (col_mid + 120), 16, Qt.AlignLeft | Qt.AlignVCenter, "Name")
            y += 18
            p.setPen(QPen(Qt.black, 1))
            p.drawLine(left, y, right, y)
            y += 12
            p.setPen(Qt.black)

            p.setFont(body)
            row_h = 16
            items = self._rows[:6]
            left_items = items[:3]
            right_items = items[3:6]

            yy = y
            for i in range(3):
                if i < len(left_items):
                    c, n = left_items[i]
                    p.drawText(left, yy, 110, row_h, Qt.AlignLeft | Qt.AlignVCenter, c)
                    p.drawText(left + 110, yy, col_mid - (left + 110), row_h, Qt.AlignLeft | Qt.AlignVCenter, n)
                if i < len(right_items):
                    c, n = right_items[i]
                    p.drawText(col_mid + 10, yy, 110, row_h, Qt.AlignLeft | Qt.AlignVCenter, c)
                    p.drawText(col_mid + 120, yy, right - (col_mid + 120), row_h, Qt.AlignLeft | Qt.AlignVCenter, n)
                yy += row_h + 6

            return yy

        # render by template
        if tid == "boxed":
            draw_table(y + 6, boxed=True)
        elif tid == "compact":
            draw_table(y, dense=True)
        elif tid == "code_first":
            draw_table(y, code_scale=1.2)
        elif tid == "outline":
            draw_outline(y)
        elif tid == "two_column":
            draw_two_column(y)
        else:
            draw_table(y)

        if tid == "institutional":
            p.setFont(QFont(fam, 8, QFont.Normal, False))
            p.drawText(left, paper_y + paper_h - 16, right - left, 14, Qt.AlignLeft | Qt.AlignVCenter, "Generated by NHMC-Labelling")
            p.drawText(left, paper_y + paper_h - 16, right - left, 14, Qt.AlignRight | Qt.AlignVCenter, "Page 1")

        p.end()
        self.preview.setPixmap(pm)


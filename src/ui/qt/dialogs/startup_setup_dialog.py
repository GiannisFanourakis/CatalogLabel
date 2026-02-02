from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QGroupBox, QFileDialog, QLineEdit, QFormLayout, QMessageBox, QTextEdit
)

from src.services.rules.excel_loader import load_rules_xlsx
from src.services.rules.rules_types import RulesWorkbook, RulesProfile


@dataclass(frozen=True)
class StartupSetupResult:
    mode: str  # "free" | "rules"
    rules: Optional[RulesWorkbook]
    profile_id: Optional[str]
    level_labels_override: Optional[Dict[int, str]]
    institution_override: Optional[str]
    discipline_override: Optional[str]


def _norm(s: object) -> str:
    return " ".join(str(s).strip().split()) if s is not None else ""


class StartupSetupDialog(QDialog):
    """
    Startup gate:
      - Free Typing OR Rules Mode
      - If Rules Mode: user must load an Excel
      - After load: auto-detect + show everything; user can edit Institution/Discipline + level labels
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("LabelForge — Setup")
        self.setModal(True)
        self.setMinimumWidth(820)
        self.setMinimumHeight(420)

        self.rules: RulesWorkbook | None = None
        self.profile_id: str | None = None
        self.rules_path: Path | None = None

        self._build_ui()
        self._wire()
        self._refresh_enabled()

    def result_data(self) -> StartupSetupResult:
        if self.rb_free.isChecked():
            return StartupSetupResult("free", None, None, None, None, None)

        # Rules mode
        labels: Dict[int, str] = {}
        for lv, ed in self.level_edits.items():
            t = ed.text().strip()
            if t:
                labels[lv] = t

        inst = self.ed_institution.text().strip() or None
        disc = self.ed_discipline.text().strip() or None

        return StartupSetupResult(
            mode="rules",
            rules=self.rules,
            profile_id=self.profile_id,
            level_labels_override=(labels or None),
            institution_override=inst,
            discipline_override=disc,
        )

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        title = QLabel("Choose how you want to run the app")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        outer.addWidget(title)

        # Mode
        gb = QGroupBox("Mode")
        vb = QVBoxLayout(gb)
        self.rb_free = QRadioButton("Free Typing (no rules)")
        self.rb_rules = QRadioButton("Rules Mode (load Excel)")
        self.rb_free.setChecked(True)
        vb.addWidget(self.rb_free)
        vb.addWidget(self.rb_rules)
        outer.addWidget(gb)

        # Load strip
        strip = QHBoxLayout()
        self.lbl_file = QLabel("No Excel loaded.")
        self.lbl_file.setStyleSheet("color: #bbb;")
        self.btn_load = QPushButton("Load Excel…")
        strip.addWidget(self.lbl_file, 1)
        strip.addWidget(self.btn_load, 0)
        outer.addLayout(strip)

        # Review group
        self.gb_review = QGroupBox("Review (auto-detected)")
        form = QFormLayout(self.gb_review)
        form.setLabelAlignment(Qt.AlignLeft)

        # Institution / Discipline (examples)
        self.ed_institution = QLineEdit()
        self.ed_institution.setPlaceholderText("e.g. Vienna Natural History Museum")
        self.ed_discipline = QLineEdit()
        self.ed_discipline.setPlaceholderText("e.g. Vertebrate Collection")

        # Level labels (examples)
        self.level_edits: Dict[int, QLineEdit] = {}
        placeholders = {
            1: "e.g. Collection",
            2: "e.g. Subcollection",
            3: "e.g. Group",
            4: "e.g. Specimen",
        }
        for lv in (1, 2, 3, 4):
            ed = QLineEdit()
            ed.setPlaceholderText(placeholders.get(lv, f"Level {lv}"))
            self.level_edits[lv] = ed

            lbl = QLabel(f"Level {lv} label:")
            lbl.setMinimumWidth(110)  # prevent truncation
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            form.addRow(lbl, ed)

        # Put institution/discipline first (with non-truncating labels)
        lbl_i = QLabel("Institution:")
        lbl_i.setMinimumWidth(110)
        lbl_i.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.insertRow(0, lbl_i, self.ed_institution)

        lbl_d = QLabel("Discipline:")
        lbl_d.setMinimumWidth(110)
        lbl_d.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.insertRow(1, lbl_d, self.ed_discipline)

        outer.addWidget(self.gb_review)

        # Detected config text
        self.txt_detected = QTextEdit()
        self.txt_detected.setReadOnly(True)
        self.txt_detected.setMinimumHeight(90)
        outer.addWidget(self.txt_detected)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_exit = QPushButton("Exit")
        self.btn_continue = QPushButton("Continue")
        self.btn_continue.setDefault(True)
        btns.addWidget(self.btn_exit)
        btns.addWidget(self.btn_continue)
        outer.addLayout(btns)

    def _wire(self) -> None:
        self.rb_free.toggled.connect(self._refresh_enabled)
        self.rb_rules.toggled.connect(self._refresh_enabled)
        self.btn_load.clicked.connect(self._on_load_excel)
        self.btn_exit.clicked.connect(self.reject)
        self.btn_continue.clicked.connect(self._on_continue)

    def _refresh_enabled(self) -> None:
        rules_on = self.rb_rules.isChecked()
        self.btn_load.setEnabled(rules_on)                   # cannot load Excel in Free mode
        self.gb_review.setEnabled(rules_on and self.rules is not None)
        self.txt_detected.setEnabled(rules_on and self.rules is not None)

        if self.rb_free.isChecked():
            self.btn_continue.setEnabled(True)
        else:
            self.btn_continue.setEnabled(self.rules is not None and self.profile_id is not None)

    def _on_load_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Excel", str(Path.cwd()), "Excel (*.xlsx)")
        if not path:
            return

        self.rules_path = Path(path)
        self.lbl_file.setText(self.rules_path.name)
        self.lbl_file.setStyleSheet("")

        try:
            self.rules = load_rules_xlsx(path)
        except Exception as e:
            QMessageBox.critical(self, "Load Excel Failed", str(e))
            self.rules = None
            self.profile_id = None
            self.txt_detected.setPlainText("")
            self._refresh_enabled()
            return

        # Choose first profile
        pid, prof = sorted(self.rules.profiles.items(), key=lambda kv: kv[0].lower())[0]
        self.profile_id = pid

        # Auto-fill Institution/Discipline if provided by workbook (simple authority loader sets these)
        inst = (self.rules.settings.get("institution") or "").strip()
        disc = (self.rules.settings.get("discipline") or "").strip()
        if inst:
            self.ed_institution.setText(inst)
        if disc:
            self.ed_discipline.setText(disc)

        # Fill level labels
        for lv, ed in self.level_edits.items():
            ed.setText(prof.level_labels.get(lv, ""))

        # Detected summary
        delim = prof.code_delimiter or "."
        summary = []
        summary.append(f"Loaded: {self.rules_path.name}")
        summary.append(f"Profile: {prof.profile_name} ({pid})")
        summary.append(f"Levels: {prof.level_count}   | delimiter: '{delim}'")
        summary.append(f"Mappings loaded: {len(self.rules.mappings)}")
        self.txt_detected.setPlainText("\n".join(summary))

        self._refresh_enabled()

    def _on_continue(self) -> None:
        if self.rb_free.isChecked():
            self.accept()
            return

        if self.rules is None or self.profile_id is None:
            QMessageBox.warning(self, "Rules Mode", "Load an Excel file first.")
            return

        # Require at least level 1 & 2 labels (because the main UI uses them)
        if not self.level_edits[1].text().strip() or not self.level_edits[2].text().strip():
            QMessageBox.warning(self, "Missing info", "Please provide Level 1 and Level 2 labels.")
            return

        self.accept()





from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from src.ui.qt.widgets.autocomplete_combo import AutoCompleteCombo


class LevelRowWidget(QWidget):
    def __init__(self, level: int, level_label: str, parent=None):
        super().__init__(parent)
        self.level = level

        self.lbl = QLabel(level_label)
        self.cbo_code = AutoCompleteCombo()
        self.cbo_name = AutoCompleteCombo()
        self.btn_remove = QPushButton("Remove")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.lbl, 0)
        lay.addWidget(QLabel("Code:"), 0)
        lay.addWidget(self.cbo_code, 1)
        lay.addWidget(QLabel("Name:"), 0)
        lay.addWidget(self.cbo_name, 2)
        lay.addWidget(self.btn_remove, 0)

    def get_values(self) -> tuple[str, str]:
        return self.cbo_code.currentText().strip(), self.cbo_name.currentText().strip()

    def set_values(self, code: str, name: str) -> None:
        self.cbo_code.setCurrentText(code or "")
        self.cbo_name.setCurrentText(name or "")

    def lock_name(self, locked: bool) -> None:
        self.cbo_name.set_locked(locked)


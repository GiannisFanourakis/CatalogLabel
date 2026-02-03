from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox


class AutoCompleteCombo(QComboBox):
    """
    Editable dropdown that updates its list as the user types.
    Supports locking (read-only behavior) for canonical rule-enforced fields.
    """
    textEdited = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)

        self._locked = False
        self.lineEdit().textEdited.connect(self.textEdited.emit)

    def set_suggestions(self, items: list[str]) -> None:
        cur = self.currentText()
        self.blockSignals(True)
        self.clear()
        self.addItems(items)
        self.setCurrentText(cur)
        self.blockSignals(False)

    def set_locked(self, locked: bool) -> None:
        self._locked = bool(locked)
        # lock the editor but still show value
        if self.isEditable() and self.lineEdit() is not None:
            self.lineEdit().setReadOnly(self._locked)
        self.setEnabled(True)  # keep visible even when locked


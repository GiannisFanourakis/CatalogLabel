from __future__ import annotations

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


# Museum Dark: charcoal + warm bronze accents (serious, institutional)
MUSEUM_QSS = r"""
/* --- Global baseline --- */
* {
    font-family: "Segoe UI";
    font-size: 10pt;
}

QWidget {
    background-color: #0c0f14;   /* charcoal */
    color: #e8e2d6;              /* warm “paper” text */
}

/* ---- Titles / headers ---- */
QLabel#Title {
    font-size: 18px;
    font-weight: 800;
    color: #f2ede2;
    padding: 2px 2px 8px 2px;
}
QLabel#Status {
    color: #b9b2a6;
}

/* --- Group boxes: museum panel look --- */
QGroupBox {
    background-color: #121722;
    border: 1px solid #2a3242;
    border-radius: 12px;
    margin-top: 12px;
    padding: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #d8cfbf;
    font-weight: 700;
    letter-spacing: 0.3px;
}

/* --- Inputs (NO WHITE) --- */
QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    background-color: #0f141d;
    color: #f0eadf;
    border: 1px solid #343e51;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #b08d57;  /* bronze selection */
    selection-color: #0c0f14;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #b08d57; /* bronze focus ring */
}

/* Placeholder text */
QLineEdit[echoMode="0"] { /* normal line edit */
}
QLineEdit::placeholder {
    color: #8f8a80;
}

/* --- Combo dropdown + list --- */
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView {
    background: #0f141d;
    color: #f0eadf;
    border: 1px solid #343e51;
    selection-background-color: #b08d57;
    selection-color: #0c0f14;
}

/* --- Buttons: bronze primary, steel secondary --- */
QPushButton {
    background-color: #b08d57;   /* bronze */
    color: #0c0f14;
    border: 1px solid #b08d57;
    border-radius: 10px;
    padding: 9px 14px;
    font-weight: 800;
}
QPushButton:hover {
    background-color: #c09a61;
    border-color: #c09a61;
}
QPushButton:pressed {
    background-color: #9a7a49;
    border-color: #9a7a49;
}
QPushButton:disabled {
    background-color: #1a2130;
    color: #6f6a62;
    border: 1px solid #2a3242;
}

/* Optional: “secondary” buttons by objectName */
QPushButton#Secondary {
    background-color: #1a2130;
    color: #e8e2d6;
    border: 1px solid #343e51;
}
QPushButton#Secondary:hover {
    border: 1px solid #b08d57;
}

/* --- Checkboxes --- */
QCheckBox { spacing: 10px; color: #d8cfbf; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid #343e51;
    background: #0f141d;
}
QCheckBox::indicator:checked {
    background: #b08d57;
    border: 1px solid #b08d57;
}

/* --- Scroll areas and scrollbars --- */
QScrollArea {
    border: 1px solid #2a3242;
    border-radius: 12px;
    background: #0c0f14;
}
QScrollBar:vertical {
    background: #0c0f14;
    width: 12px;
    margin: 8px 4px 8px 4px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #2a3242;
    min-height: 30px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover { background: #394459; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

/* --- Menus (Windows loves to ignore these unless explicit) --- */
QMenuBar { background: #121722; color: #e8e2d6; }
QMenuBar::item:selected { background: #1a2130; }
QMenu { background: #121722; color: #e8e2d6; border: 1px solid #2a3242; }
QMenu::item:selected { background: #b08d57; color: #0c0f14; }

/* --- Separators --- */
QFrame[frameShape="4"] { color: #2a3242; }
"""


def apply_museum_theme(app: QApplication) -> None:
    # Force Fusion so Windows theme can't “helpfully” turn things white.
    app.setStyle("Fusion")

    pal = QPalette()

    # Core surfaces
    pal.setColor(QPalette.Window, QColor("#0c0f14"))
    pal.setColor(QPalette.WindowText, QColor("#e8e2d6"))
    pal.setColor(QPalette.Base, QColor("#0f141d"))
    pal.setColor(QPalette.AlternateBase, QColor("#121722"))
    pal.setColor(QPalette.Text, QColor("#e8e2d6"))

    # Buttons
    pal.setColor(QPalette.Button, QColor("#121722"))
    pal.setColor(QPalette.ButtonText, QColor("#e8e2d6"))

    # Highlights (bronze)
    pal.setColor(QPalette.Highlight, QColor("#b08d57"))
    pal.setColor(QPalette.HighlightedText, QColor("#0c0f14"))

    # Tooltips
    pal.setColor(QPalette.ToolTipBase, QColor("#121722"))
    pal.setColor(QPalette.ToolTipText, QColor("#e8e2d6"))

    app.setPalette(pal)
    app.setStyleSheet(MUSEUM_QSS)


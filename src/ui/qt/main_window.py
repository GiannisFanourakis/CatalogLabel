from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QFileDialog,
)

from src import __version__
from src.app_info import APP_NAME, APP_AUTHOR, APP_URL
from src.ui.qt.views.label_editor_view import LabelEditorView


class MainWindow(QMainWindow):
    """
    Main window:
    - Hosts LabelEditorView (HierarchyEditor-based)
    - Focused workflow for building and exporting label hierarchies
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(APP_NAME)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.editor = LabelEditorView(self)
        layout.addWidget(self.editor)

        self.setCentralWidget(central)

        self._build_menu()

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        export_pdf_action = QAction("Export &PDF…", self)
        export_pdf_action.setShortcut(QKeySequence("Ctrl+E"))
        export_pdf_action.triggered.connect(self._export_pdf)
        file_menu.addAction(export_pdf_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

    def _export_pdf(self) -> None:
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            "labels.pdf",
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return

        try:
            self.editor.export_pdf(save_path)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Export failed", str(exc))

    def _about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            f"CatalogLabel v{__version__}\n\n"
            "Structured label & classification generator.\n"
            "Free Typing and Rules Mode (Excel).\n"
            "Exports print-ready PDFs.\n\n"
            "Created by Ioannis Fanourakis\n"
            "Open-source software.",
        )







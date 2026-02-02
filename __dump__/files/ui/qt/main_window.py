from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QFileDialog,
)

from src.ui.qt.views.label_editor_view import LabelEditorView


class MainWindow(QMainWindow):
    """
    Current-state main window:
    - Hosts LabelEditorView (HierarchyEditor-based)
    - No legacy subcollection UI, no legacy buttons.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NHMC Labelling")

        self.editor = LabelEditorView()
        self.setCentralWidget(self._wrap(self.editor))

        self._build_menu()
        self.statusBar().showMessage("Ready.")

    def _wrap(self, w: QWidget) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(w)
        return host

    def _build_menu(self) -> None:
        mb = self.menuBar()
        m_file = mb.addMenu("&File")
        m_help = mb.addMenu("&Help")

        act_load_excel = QAction("Load Rules Excel…", self)
        act_load_excel.setShortcut(QKeySequence("Ctrl+O"))
        act_load_excel.triggered.connect(self._load_excel)
        m_file.addAction(act_load_excel)

        act_export_pdf = QAction("Export PDF…", self)
        act_export_pdf.setShortcut(QKeySequence("Ctrl+E"))
        act_export_pdf.triggered.connect(lambda: self.editor._export_pdf_clicked())
        m_file.addAction(act_export_pdf)

        m_file.addSeparator()

        act_save_cache = QAction("Save Cache", self)
        act_save_cache.setShortcut(QKeySequence("Ctrl+S"))
        act_save_cache.triggered.connect(lambda: self.editor._save_cache_clicked())
        m_file.addAction(act_save_cache)

        m_file.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        act_about = QAction("About", self)
        act_about.triggered.connect(self._about)
        m_help.addAction(act_about)

    def _load_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load rules.xlsx", "", "Excel (*.xlsx)")
        if not path:
            return

        ok = self.editor.load_rules_from_path(path)
        if ok:
            self.statusBar().showMessage(f"Loaded Excel: {path}", 5000)
            # Force Rules Mode ON
            if self.editor.mode.currentIndex() != 1:
                self.editor.mode.setCurrentIndex(1)
        else:
            QMessageBox.warning(self, "Load failed", "Could not load the Excel rules file.")

    def _about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            "NHMC Labelling\n\nTree-first label builder with Rules Mode (Excel) + Free Typing (cached autocomplete).",
        )

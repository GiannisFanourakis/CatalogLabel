from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from src.ui.qt.theme import apply_museum_theme
from src.ui.qt.main_window import MainWindow


def _set_windows_app_id(app_id: str) -> None:
    """
    Ensures Windows taskbar grouping + App identity are correct.
    Safe no-op on non-Windows platforms.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes  # stdlib
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def main() -> int:
    # Set AppUserModelID before creating any windows (Windows taskbar identity)
    _set_windows_app_id("nhmc.labelforge")

    app = QApplication(sys.argv)

    # Qt application identity (used by OS/UI in various places)
    app.setApplicationName("LabelForge")
    app.setOrganizationName("NHMC")
    app.setOrganizationDomain("nhmc.uoc.gr")

    apply_museum_theme(app)

    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

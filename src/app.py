from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.ui.qt.theme import apply_museum_theme
from src.ui.qt.main_window import MainWindow


def _set_windows_app_id(app_id: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes  # pylint: disable=import-outside-toplevel
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        return


def _icon_from_resources() -> Optional[QIcon]:
    """
    Load icon files shipped inside src/resources/icons.
    Uses importlib.resources so it works in dev and when frozen (PyInstaller).
    """
    try:
        from importlib.resources import files  # py3.9+
        base = files("src.resources.icons")
        ico = base / "CatalogLabel.ico"
        png = base / "CatalogLabel.png"

        if ico.is_file():
            return QIcon(str(ico))
        if png.is_file():
            return QIcon(str(png))
        return None
    except Exception:
        return None


def main() -> int:
    app = QApplication(sys.argv)

    app.setApplicationName("CatalogLabel")
    app.setOrganizationName("Ioannis Fanourakis")
    app.setOrganizationDomain("")

    _set_windows_app_id("ioannisfanourakis.CatalogLabel")

    apply_museum_theme(app)

    icon = _icon_from_resources()
    if icon is not None and not icon.isNull():
        app.setWindowIcon(icon)

    w = MainWindow()
    if icon is not None and not icon.isNull():
        w.setWindowIcon(icon)

    w.resize(1200, 800)
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())



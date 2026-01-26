"""GUI runner for Mandala application."""

import logging

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from ..utils import IconFilename, Paths, initialize_logging
from .mainwindow import MandalaMainWindow

logger = logging.getLogger(__name__)

try:  # Windows only for taskbar icon
    from ctypes import windll

    myappid = "wonyoungjang.mandala.random_file_copier.0.0.1"
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


def main() -> None:
    """Run the application."""
    initialize_logging()
    logger.info("Start: Mandala GUI")

    app = QApplication()
    app.setWindowIcon(QIcon(str(Paths.icon(IconFilename.WINDOW))))
    apply_stylesheet(app, theme="dark_purple.xml", extra={"density_scale": "-2"})
    w = MandalaMainWindow()
    w.show()
    app.exec()

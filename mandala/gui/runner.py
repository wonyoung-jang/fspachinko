"""GUI runner for Mandala application."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ..config.loggers import initialize_logging
from .mainwindow import MandalaMainWindow

logger = logging.getLogger(__name__)

basedir = Path(__file__).parent.parent.parent
window_icon = str(basedir / "icons" / "windowIcon.png")

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
    app.setWindowIcon(QIcon(window_icon))
    w = MandalaMainWindow()
    w.show()
    app.exec()

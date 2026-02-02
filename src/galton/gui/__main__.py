"""Main entry point for GUI."""

import logging

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from ..utils import AppSetting, IconFilename, Paths, initialize_logging
from .mainwindow import MainWindow

logger = logging.getLogger(__name__)

QCoreApplication.setOrganizationName(AppSetting.ORGANIZATION)
QCoreApplication.setOrganizationDomain(AppSetting.DOMAIN)
QCoreApplication.setApplicationName(AppSetting.APPLICATION)


try:  # Windows only for taskbar icon
    from ctypes import windll

    myappid = "wonyoungjang.galton.random_file_transfer_utility.0.0.1"
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


def main() -> None:
    """Run the application."""
    initialize_logging()
    logger.info("Start: galton GUI")

    app = QApplication()
    app.setWindowIcon(QIcon(Paths.icon(IconFilename.WINDOW)))
    apply_stylesheet(app, theme="dark_purple.xml", extra={"density_scale": "-2"})
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()

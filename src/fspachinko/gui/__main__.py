"""Main entry point for GUI."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ..core import AppSetting, IconFilename, get_icon_path, initialize_logging
from .mainwindow import MainWindow

QCoreApplication.setOrganizationName(AppSetting.ORGANIZATION_NAME)
QCoreApplication.setOrganizationDomain(AppSetting.ORGANIZATION_DOMAIN)
QCoreApplication.setApplicationName(AppSetting.APPLICATION_NAME)

# Windows only for taskbar icon
try:
    from ctypes import windll

    myappid = "wonyoungjang.fspachinko.random_file_transfer_utility.0.0.1"
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


def main() -> None:
    """Run the application."""
    initialize_logging()
    app = QApplication()
    app.setWindowIcon(QIcon(get_icon_path(IconFilename.WINDOW)))
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

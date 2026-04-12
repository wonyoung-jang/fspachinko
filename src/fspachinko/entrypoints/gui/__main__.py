"""Qt GUI entry point."""

from enum import StrEnum

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from fspachinko.bootstrap import Bootstrapper
from fspachinko.entrypoints.gui.helpers import get_qt_icon
from fspachinko.entrypoints.gui.mainwindow import Presenter


class GUIAppSetting(StrEnum):
    """Enumeration for different settings categories."""

    APPLICATION_NAME = "fspachinko"
    ORGANIZATION_DOMAIN = "https://github.com/wonyoung-jang/fspachinko"
    ORGANIZATION_NAME = "Wonyoung Jang"
    WINDOWS_TASKBAR_APP_ID = "wonyoungjang.fspachinko.random_file_transfer_utility.0.0.1"


try:
    from ctypes import windll

    # Windows only - taskbar icon fix for PySide6
    myappid = GUIAppSetting.WINDOWS_TASKBAR_APP_ID
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


def main() -> None:
    """Run the application."""
    QCoreApplication.setOrganizationName(GUIAppSetting.ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(GUIAppSetting.ORGANIZATION_DOMAIN)
    QCoreApplication.setApplicationName(GUIAppSetting.APPLICATION_NAME)
    app = QApplication()
    app.setWindowIcon(get_qt_icon("window"))
    bootstrapper = Bootstrapper()
    window = Presenter(bootstrapper=bootstrapper)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

"""Qt GUI entry point."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from fspachinko.bootstrap import Bootstrapper
from fspachinko.entrypoints.gui.helpers import get_qt_icon
from fspachinko.entrypoints.gui.mainwindow import Presenter
from fspachinko.fp import Fp

try:
    from ctypes import windll

    # Windows only - taskbar icon fix for PySide6
    myappid = Fp.AppSetting.WINDOWS_TASKBAR_APP_ID
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass


def main() -> None:
    """Run the application."""
    QCoreApplication.setOrganizationName(Fp.AppSetting.ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(Fp.AppSetting.ORGANIZATION_DOMAIN)
    QCoreApplication.setApplicationName(Fp.AppSetting.APPLICATION_NAME)
    app = QApplication()
    app.setWindowIcon(get_qt_icon("windowIcon.png"))
    bootstrapper = Bootstrapper()
    window = Presenter(bootstrapper=bootstrapper)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

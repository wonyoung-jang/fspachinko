"""Qt GUI entry point."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from fspachinko.adapters.loggers import initialize_logging
from fspachinko.bootstrap import bootstrap

from .constants_gui import GUIAppSetting
from .mainwindow import MainWindow
from .qthelpers import window_icon

QCoreApplication.setOrganizationName(GUIAppSetting.ORGANIZATION_NAME)
QCoreApplication.setOrganizationDomain(GUIAppSetting.ORGANIZATION_DOMAIN)
QCoreApplication.setApplicationName(GUIAppSetting.APPLICATION_NAME)

# Windows only - taskbar icon fix
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
    app.setWindowIcon(window_icon())
    bus, pipeline = bootstrap()
    window = MainWindow(bus, pipeline)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

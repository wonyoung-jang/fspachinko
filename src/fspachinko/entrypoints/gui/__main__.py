"""Qt GUI entry point."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from fspachinko.adapters.loggers import initialize_logging
from fspachinko.constants import AppSetting

from .mainwindow import MainWindow
from .qthelpers import window_icon

q_core_app = QCoreApplication
q_core_app.setOrganizationName(AppSetting.ORGANIZATION_NAME)
q_core_app.setOrganizationDomain(AppSetting.ORGANIZATION_DOMAIN)
q_core_app.setApplicationName(AppSetting.APPLICATION_NAME)

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
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

"""GUI runner for Mandala application."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QApplication

from ..config.loggers import initialize_logging
from .mainwindow import MandalaMainWindow

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the application."""
    initialize_logging()

    logger.info("Start: Mandala GUI")

    app = QApplication()

    gui = MandalaMainWindow()
    gui.show()

    app.exec()

    logger.info("End: Mandala GUI")


if __name__ == "__main__":
    main()

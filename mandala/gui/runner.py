"""GUI runner for Mandala application."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QApplication

from ..config.loggers import initialize_logging
from .mainwindow import MandalaMainWindow
from .stylesheet import load_stylesheet

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the application."""
    initialize_logging()
    logger.info("Start: Mandala GUI")
    app = QApplication()

    # Load and apply stylesheet
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)
        logger.info("Stylesheet loaded successfully")
    else:
        logger.warning("Running without stylesheet")

    gui = MandalaMainWindow()
    gui.show()
    app.exec()
    logger.info("End: Mandala GUI")


if __name__ == "__main__":
    main()

"""GUI runner for Mandala application."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from mandala.gui.main_window import MainWindow


def main() -> None:
    """Run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    stylesheet = Path("CRFStyleSheet.qss")
    with stylesheet.open() as f:
        style = f.read()
        window.setStyleSheet(style)
    sys.exit(app.exec())

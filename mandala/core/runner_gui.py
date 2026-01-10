"""GUI runner for Mandala application."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..gui.main_window import MandalaMainWindow


def main() -> None:
    """Run the application."""
    app = QApplication()
    gui = MandalaMainWindow()
    gui.show()
    app.exec()

"""GUI runner for Mandala application."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from mandala.gui.main_window import MandalaMainGui


def main() -> None:
    """Run the application."""
    app = QApplication()
    gui = MandalaMainGui()
    gui.show()
    app.exec()

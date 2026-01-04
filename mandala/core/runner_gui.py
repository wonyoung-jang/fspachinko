"""GUI runner for Mandala application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from mandala.gui.main_window import MainWindow


def main() -> None:
    """Run the application."""
    app = QApplication()
    window = MainWindow()
    stylesheet = Path("CRFStyleSheet.qss")
    stylesheet_str = stylesheet.read_text()
    window.setStyleSheet(stylesheet_str)
    window.show()
    app.exec()

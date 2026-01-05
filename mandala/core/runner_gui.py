"""GUI runner for Mandala application."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from mandala.gui.main_window import MainWindow


def main() -> None:
    """Run the application."""
    app = QApplication()
    gui = MainWindow()
    gui.show()
    app.exec()

    for k, v in sorted(gui.__dict__.items()):
        print(f"{k}: {v}")
    print(len(gui.__dict__))

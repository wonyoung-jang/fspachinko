"""GUI runner for Mandala application."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from mandala.gui.main_window import MandalaMainGui


def main() -> None:
    """Run the application."""
    app = QApplication()
    gui = MandalaMainGui()
    prekeys = sorted(gui.__dict__.keys())
    for key in prekeys:
        print(f"{key}")
    print(len(prekeys))

    gui.show()
    app.exec()

    post_keys = sorted(gui.__dict__.keys())
    for key in post_keys:
        print(f"{key}")
    print(len(post_keys))

    print("Diff")
    print(set(post_keys) - set(prekeys))

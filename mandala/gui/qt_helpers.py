"""Helper functions for Qt GUI."""

from __future__ import annotations

from PySide6.QtWidgets import QSpinBox


def create_spinbox(minimum: int, maximum: int, *, enabled: bool) -> QSpinBox:
    """Create and configure a QSpinBox widget."""
    name = QSpinBox(
        minimum=minimum,
        maximum=maximum,
    )
    name.setEnabled(enabled)
    return name

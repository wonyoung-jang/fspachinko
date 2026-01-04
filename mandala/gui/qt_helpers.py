"""Helper functions for Qt GUI."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox


def make_spinbox(lo: int, hi: int, *, enabled: bool) -> QSpinBox:
    """Create and configure a QSpinBox widget."""
    name = QSpinBox()
    name.setRange(lo, hi)
    name.setMaximumWidth(60)
    name.setEnabled(enabled)
    return name


def make_group_button(name: str) -> QPushButton:
    """Create and configure a group button."""
    button = QPushButton(name)
    button.setFlat(True)
    button.setCheckable(True)
    button.setChecked(True)
    button.setObjectName("groupButton")
    return button


def make_group_label(name: str) -> QLabel:
    """Create and configure a group label."""
    label = QLabel(name)
    label.setObjectName("groupLabel")
    return label

"""GUI components in PySide6 for mandala."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from mandala.gui.main_window import QSpinBox

if TYPE_CHECKING:
    from collections.abc import Sequence


class PathSelectorWidget(QGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.combo = QComboBox()

        layout = QHBoxLayout(self)
        layout.addWidget(self.combo)


class RangeFilterWidget(QGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Weight."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.min_spin = QSpinBox(minimum=0, maximum=1_000_000)
        self.max_spin = QSpinBox(minimum=0, maximum=1_000_000)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Min"), 0, 0)
        layout.addWidget(self.min_spin, 0, 1)
        layout.addWidget(QLabel("Max"), 1, 0)
        layout.addWidget(self.max_spin, 1, 1)


class DblRangeFilterWidget(QGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Size or Duration."""

    def __init__(self, title: str, suffix_options: Sequence[str], parent: QWidget | None = None) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.min_spin = QDoubleSpinBox(minimum=0, maximum=1_000_000)
        self.max_spin = QDoubleSpinBox(minimum=0, maximum=1_000_000)

        # Connect logic internally
        self.min_spin.editingFinished.connect(self.validate_range)
        self.max_spin.editingFinished.connect(self.validate_range)

        self.combo = QComboBox()
        self.combo.addItems(suffix_options)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Min"), 0, 0)
        layout.addWidget(self.min_spin, 0, 1)
        layout.addWidget(QLabel("Max"), 1, 0)
        layout.addWidget(self.max_spin, 1, 1)
        layout.addWidget(self.combo, 0, 2, 2, 1)

    def validate_range(self) -> None:
        """Auto-corrects if Min > Max."""
        if self.min_spin.value() > self.max_spin.value():
            min_spin_val = self.min_spin.value()
            self.min_spin.setValue(self.max_spin.value())
            self.max_spin.setValue(min_spin_val)

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "enabled": self.isChecked(),
            "min": self.min_spin.value(),
            "max": self.max_spin.value(),
            "unit": self.combo.currentText() if self.combo else None,
        }


class DualListWidget(QGroupBox):
    """Handles the Include/Exclude pattern for Keywords and Extensions."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, parent)
        self.setFlat(True)

        self.include_edit = QLineEdit()
        self.exclude_edit = QLineEdit()

        layout = QGridLayout(self)

        # Sub-groups for visual clarity
        self.include_groupbox = QGroupBox("Include", checkable=True, flat=True)
        QHBoxLayout(self.include_groupbox).addWidget(self.include_edit)

        self.exclude_groupbox = QGroupBox("Exclude", checkable=True, flat=True)
        QHBoxLayout(self.exclude_groupbox).addWidget(self.exclude_edit)

        switch_btn = QPushButton("Switch")
        switch_btn.clicked.connect(self.switch_text)

        layout.addWidget(self.include_groupbox, 0, 0)
        layout.addWidget(self.exclude_groupbox, 1, 0)
        layout.addWidget(switch_btn, 0, 1, 2, 1)

    def switch_text(self) -> None:
        """Switch the text between include and exclude."""
        inc, exc = self.include_edit.text(), self.exclude_edit.text()
        self.include_edit.setText(exc)
        self.exclude_edit.setText(inc)

    def get_config(self) -> dict:
        """Return the include and exclude lists."""
        return {
            "include": self.include_edit.text(),
            "exclude": self.exclude_edit.text(),
        }

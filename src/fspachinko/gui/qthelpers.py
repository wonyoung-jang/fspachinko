"""Helper functions for Qt GUI elements."""

from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QWidget,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from PySide6.QtCore import QObject
    from PySide6.QtGui import QAction


def get_qt_classname(obj: QObject) -> str:
    """Get the class name of a QObject."""
    return str(obj.metaObject().className())


def set_qt_name(w: QWidget | QAction, name: str) -> None:
    """Initialize a widget with a given object name."""
    w.setObjectName(name)


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    if not statustip:
        statustip = f"{tooltip} | ({get_qt_classname(w)})"

    w.setToolTip(tooltip)
    w.setStatusTip(statustip)


def get_widget_value(widget: QWidget) -> Any:
    """Retrieve the value of a widget based on its type.

    Args:
        widget (QWidget): The widget to retrieve the value from.

    Returns:
        Any: The value of the widget, or None if not applicable.

    """
    match widget:
        case QLineEdit() | QLabel():
            return widget.text()
        case QComboBox():
            return widget.currentIndex()
        case QSpinBox() | QDoubleSpinBox():
            return widget.value()
        case QGroupBox() if not widget.isCheckable():
            return None
        case QCheckBox() | QRadioButton() | QGroupBox():
            return widget.isChecked()
        case _:
            return None


def set_widget_value(widget: QWidget, val: Any) -> None:
    """Set the value of a widget based on its type.

    Args:
        widget (QWidget): The widget to set the value for.
        val (Any): The value to set.

    """
    match widget:
        case QLineEdit() | QLabel():
            widget.setText(val)
        case QComboBox():
            try:
                index = int(val)
                if 0 <= index < widget.count():
                    widget.setCurrentIndex(index)
            except ValueError, TypeError:
                pass
        case QSpinBox():
            widget.setValue(int(val))
        case QDoubleSpinBox():
            widget.setValue(float(val))
        case QCheckBox() | QRadioButton() | QGroupBox():
            widget.setChecked(val)
        case _:
            return


def iter_custom_widget(w: QWidget) -> Iterator[tuple[str, QWidget]]:
    """Iterate over valid child widgets."""
    for child in w.findChildren(QWidget):
        if (key := child.objectName()) and not key.startswith("qt_"):
            yield key, child

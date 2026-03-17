"""Helper functions for Qt GUI elements."""

from functools import cache
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon

from fspachinko.adapters.filesystemport import get_icon_path
from fspachinko.constants import IconFilename

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    if not statustip:
        statustip = f"{tooltip} | ({w.metaObject().className()})"
    w.setToolTip(tooltip)
    w.setStatusTip(statustip)


@cache
def window_icon() -> QIcon:
    """Get the window icon."""
    return QIcon(get_icon_path(IconFilename.WINDOW))


@cache
def save_icon() -> QIcon:
    """Get the save icon."""
    return QIcon(get_icon_path(IconFilename.SAVE))


@cache
def save_as_icon() -> QIcon:
    """Get the save as icon."""
    return QIcon(get_icon_path(IconFilename.SAVE_AS))


@cache
def load_icon() -> QIcon:
    """Get the load icon."""
    return QIcon(get_icon_path(IconFilename.OPEN))


@cache
def exit_icon() -> QIcon:
    """Get the exit icon."""
    return QIcon(get_icon_path(IconFilename.CLOSE))


@cache
def start_icon() -> QIcon:
    """Get the start icon."""
    return QIcon(get_icon_path(IconFilename.START))


@cache
def stop_icon() -> QIcon:
    """Get the stop icon."""
    return QIcon(get_icon_path(IconFilename.STOP))


@cache
def browse_icon() -> QIcon:
    """Get the browse icon."""
    return QIcon(get_icon_path(IconFilename.BROWSE))


@cache
def open_dir_icon() -> QIcon:
    """Get the open directory icon."""
    return QIcon(get_icon_path(IconFilename.OPEN_DIR))

"""Helper functions for Qt GUI elements."""

from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon, QKeySequence

from fspachinko.datapaths import get_icon_path

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget


class QtActionKey(StrEnum):
    """Declarative keys for icons and shortcuts."""

    SAVE = "save"
    SAVE_AS = "save_as"
    LOAD = "load"
    EXIT = "exit"
    START = "start"
    STOP = "stop"


@cache
def menu_config() -> dict[str, Sequence[QtActionKey | None]]:
    """Return a dictionary mapping menu names to sequences of QtActionKeys."""
    return {
        "&File": (
            QtActionKey.SAVE,
            QtActionKey.SAVE_AS,
            QtActionKey.LOAD,
            None,
            QtActionKey.EXIT,
        ),
        "&Run": (
            QtActionKey.START,
            QtActionKey.STOP,
        ),
    }


@cache
def toolbar_config() -> Sequence[QtActionKey | None]:
    """Return a sequence of QtActionKeys for the toolbar."""
    return (
        QtActionKey.SAVE,
        QtActionKey.SAVE_AS,
        QtActionKey.LOAD,
        None,
        QtActionKey.START,
        QtActionKey.STOP,
        None,
        QtActionKey.EXIT,
    )


@dataclass(slots=True, frozen=True)
class QtActionConfig:
    """Configuration for a Qt action."""

    name: QtActionKey
    text: str
    tip: str
    shortcut: str
    iconfile: str


@cache
def qt_action_config() -> Sequence[QtActionConfig]:
    """Return a sequence of QtActionConfig for the application."""
    return (
        QtActionConfig(
            name=QtActionKey.SAVE,
            text="&Save Configuration",
            tip="Save current configuration (Ctrl+S)",
            shortcut="Ctrl+S",
            iconfile="save_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        ),
        QtActionConfig(
            name=QtActionKey.SAVE_AS,
            text="Save Configuration &As",
            tip="Save current configuration as ... (Ctrl+Shift+S)",
            shortcut="Ctrl+Shift+S",
            iconfile="save_as_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        ),
        QtActionConfig(
            name=QtActionKey.LOAD,
            text="&Load Configuration",
            tip="Load configuration (Ctrl+O)",
            shortcut="Ctrl+O",
            iconfile="file_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        ),
        QtActionConfig(
            name=QtActionKey.EXIT,
            text="&Exit",
            tip="Exit application (Ctrl+W)",
            shortcut="Ctrl+W",
            iconfile="close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        ),
        QtActionConfig(
            name=QtActionKey.START,
            text="&Start",
            tip="Start (Ctrl+R)",
            shortcut="Ctrl+R",
            iconfile="play_arrow_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        ),
        QtActionConfig(
            name=QtActionKey.STOP,
            text="S&top",
            tip="Stop (ESC)",
            shortcut="ESC",
            iconfile="stop_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        ),
    )


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    w.setToolTip(tooltip)
    w.setStatusTip(statustip or tooltip)


@cache
def get_qt_icon(filename: str) -> QIcon:
    """Get cached icon by declarative name."""
    if filename:
        return QIcon(get_icon_path(filename))
    msg = f"Unknown icon: {filename}"
    raise ValueError(msg)


@cache
def get_qt_shortcut(shortcut: str) -> QKeySequence:
    """Get cached shortcut by declarative name."""
    if shortcut:
        return QKeySequence(shortcut)
    msg = f"Unknown shortcut: {shortcut}"
    raise ValueError(msg)

"""Actions module for QActions."""

from dataclasses import dataclass

from PySide6.QtGui import QAction

from .qthelpers import ACTION_CONFIG, set_qt_tips


@dataclass(slots=True)
class Actions:
    """Main file menu actions."""

    save: QAction
    save_as: QAction
    load: QAction
    exit: QAction
    start: QAction
    stop: QAction

    @classmethod
    def build(cls) -> Actions:
        """Get file menu actions."""
        actions = {}
        for name, (icon, text, shortcut, tip) in ACTION_CONFIG.items():
            action = QAction(icon(), text, shortcut=shortcut())
            set_qt_tips(action, tip)
            actions[name] = action
        return cls(**actions)

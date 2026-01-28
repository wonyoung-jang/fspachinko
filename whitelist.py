"""Whitelist for vulture."""

from file_roulette.gui.components import PathSelectorWidget

PathSelectorWidget.dragEnterEvent  # noqa: B018
PathSelectorWidget.dropEvent  # noqa: B018

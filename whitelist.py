"""Whitelist for vulture."""

from fspachinko.entrypoints.gui.components import PathSelectorWidget

PathSelectorWidget.dragEnterEvent  # noqa: B018
PathSelectorWidget.dropEvent  # noqa: B018

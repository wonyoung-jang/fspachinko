"""Whitelist for vulture."""

from mandala.gui.components import PathSelectorWidget

PathSelectorWidget.dragEnterEvent  # noqa: B018
PathSelectorWidget.dropEvent  # noqa: B018

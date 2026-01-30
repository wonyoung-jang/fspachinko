"""Main package for file-roulette."""

from .cli.cli import main as main_cli
from .gui.gui import main as main_gui

__all__ = ["main_cli", "main_gui"]


def hello(n: int) -> str:
    """Return a hello message with the sum of numbers from 1 to n."""
    return f"Hello {n}!"

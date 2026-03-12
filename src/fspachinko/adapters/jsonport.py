"""JSON port adapter for fspachinko."""

import json
from os.path import exists, isfile


def save_json(path: str, data: dict, *, sort: bool = False) -> None:
    """Save JSON data to a file."""
    with open(path, "w", encoding="utf-8") as f:
        if sort:
            data = dict(sorted(data.items(), key=lambda x: x[0]))
        json.dump(data, f, indent=4)


def load_json(path: str) -> dict:
    """Load JSON data from a file."""
    if not (exists(path) and isfile(path)):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

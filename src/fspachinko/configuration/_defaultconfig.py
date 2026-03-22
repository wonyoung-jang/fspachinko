"""A dictionary with default values for configuration settings."""

DEFAULT_CONFIG: dict = {
    "root": "C:/",
    "dest": "/fspachinko_output",
    "filecount": {
        "count": 10,
        "is_rand_enabled": False,
        "rand_min": 1,
        "rand_max": 10,
    },
    "directory": {
        "is_enabled": False,
        "name": "fsp_output",
        "count": 1,
    },
    "filename": {
        "is_enabled": False,
        "template": "{original}",
    },
    "dirname": {
        "is_enabled": False,
        "should_include": True,
        "text": "",
    },
    "keyword": {
        "is_enabled": False,
        "should_include": True,
        "text": "",
    },
    "extension": {
        "is_enabled": False,
        "should_include": True,
        "text": "",
    },
    "filesize": {
        "is_enabled": False,
        "minimum": 0.0,
        "maximum": 10.0,
        "unit": "MB",
    },
    "duration": {
        "is_enabled": False,
        "minimum": 0.0,
        "maximum": 10.0,
        "unit": "m",
    },
    "options": {
        "transfer_mode": "Dry Run",
        "max_per_dir": 0,
        "is_create_unique_folders": True,
        "should_follow_symlink": True,
        "rng_seed": None,
    },
}

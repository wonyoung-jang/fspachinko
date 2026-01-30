# File Roulette

Transfer random files from point A to point B. Customize what and how to transfer with various filters. Supports copy, move, symlink (shortcut), and hardlink transfer operations.

## Installation (uv)

```bash
uv add file-roulette
```

or

```bash
uv tool install file-roulette
```

## Usage

File Roulette can be used via command-line interface (CLI) or graphical user interface (GUI).

## Command Line Interface

### Basic Usage

```bash
# Use configuration file
file-roulette-cli --config your-file-roulette.json
```

## Graphical User Interface

### Launch GUI

```bash
file-roulette-gui
```

Or simply:

```bash
file-roulette
```

### GUI Profiles

Save frequently used configurations as profiles:

1. Configure settings in the GUI
2. Click **File → Save Profile As**
3. Name your profile (e.g., "music_copy")
4. Load later with **File → Load Profile**

## Configuration File

Create a `file-roulette.json` file for reusable configurations. Pass this to the CLI after the `--config` flag. The default (for Windows) is shown below:

```json
{
    "root": "C:/",
    "dest": "file_roulette_output/",
    "filecount": {
        "count": 20,
        "is_rand_enabled": false,
        "rand_min": 1,
        "rand_max": 12
    },
    "folder": {
        "should_create": true,
        "is_unique": true,
        "name": "test_folder_output",
        "count": 10
    },
    "filename": {
        "template": "{original}"
    },
    "transfermode": {
        "transfer_mode": "Symlink",
        "trash_empty_folder_enabled": false
    },
    "keyword": {
        "should_include": true,
        "text": ""
    },
    "extension": {
        "should_include": true,
        "text": "wav"
    },
    "filesize": {
        "is_enabled": false,
        "minimum": 0.0,
        "maximum": 0.0
    },
    "duration": {
        "is_enabled": false,
        "minimum": 0.0,
        "maximum": 0.0
    },
    "folder_size_limit": {
        "is_enabled": false,
        "size_limit": 500.0
    },
    "total_size_limit": {
        "is_enabled": false,
        "size_limit": 500.0
    },
    "options": {
        "max_per_folder": 3,
        "should_follow_symlink": false,
        "is_dry_run": true
    }
}
```

## Example Configurations

### Random Music Playlist

```json
{
    "root": "~/Music",
    "dest": "~/Playlists/Random",
    "filecount": {
        "count": 50,
        ...
    },
    ...
    "extension": {
        "should_include": true,
        "text": "wav,flac,m4a"
    },
    ...
    "options": {
        "max_per_folder": 2,
        ...
    }
}
```

### Photo Gallery Selection

```json
{
    "root": "~/Photos",
    "dest": "~/Gallery",
    "filecount": {
        "count": 20,
        ...
    },
    ...
    "extension": {
        "should_include": true,
        "text": "jpg,png"
    },
    "filesize": {
        "is_enabled": true,
        "minimum": 1.0,
        ...
    },
    "keyword": {
        "should_include": false,
        "text": "thumbnail,draft"
    },
    ...
}
```

### Video Highlights

```json
{
    "root": "~/Videos",
    "dest": "~/Highlights",
    "filecount": {
        "count": 10,
        ...
    },
    ...
    "extension": {
        "should_include": true,
        "text": "mp4"
    },
    "duration": {
        "is_enabled": true,
        "minimum": 30.0,
        "maximum": 600.0
    },
    ...
}
```

### Safe Preview (Dry Run)

```json
{
    "root": "/important/files",
    "dest": "/backup",
    "filecount": {
        "count": 100,
        ...
    },
    ...
    "options": {
        ...
        "is_dry_run": true
    }
}
```

## Advanced Features

### Output Filename Templates

Use template variables in filenames:

- `{original}`: Original filename
- `{index}`: Sequential number
- `{date}`: Current date (YYYY-MM-DD)
- `{time}`: Current time (HH-MM-SS)
- `{datetime}`: Combined date and time
- `{parent}`: Parent folder name
- `{parentstoroot}`: Full parent path separated by `-`

Example: `{index}_{original}_{date}`: `photo.jpg` -> `1_photo_2026-01-25.jpg`

### Logging

Configure logging in a `json` file. Here is the default `file_roulette_configs/logging.json` provided:

```json
{
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
        "file": {
            "format": "[%(asctime)s] %(levelname)s[%(module)s] %(message)s"
        },
        "console": {
            "format": "[%(asctime)s] %(levelname)s[%(module)s] %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "level": "INFO",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "file",
            "level": "DEBUG",
            "filename": "file-roulette.log",
            "mode": "w",
            "encoding": "utf-8",
            "delay": true
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": [
            "console",
            "file"
        ]
    }
}
```

## Troubleshooting

### Common Issues

**No files found:**
- Check your filters (extension, keyword, size)
- Verify source path exists and contains matching files
- Try `--dry-run` to see what would be selected

**Permission errors:**
- Ensure read access to source directory
- Ensure write access to destination directory
- Try running with appropriate permissions

**Hardlink errors:**
- Source and destination must be on same filesystem
- Not supported on all filesystems (e.g., FAT32)
- Falls back to symlink automatically

**Duration filter not working:**
- Requires ffmpeg installed on system
- Only works with media files (video/audio)
- Check file format is supported by ffmpeg

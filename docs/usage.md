---
icon: lucide/book-open
---

# Usage Guide

Mandala can be used via command-line interface (CLI) or graphical user interface (GUI).

## Installation

```bash
# Install using uv
uv pip install -e .

# Or with development dependencies
uv sync
```

## Command Line Interface

### Basic Usage

```bash
# Copy 10 random files
mandala-cli --root /source/path --dest /output/path --count 10

# Use configuration file
mandala-cli --config mandala.json

# Dry run (no actual transfers)
mandala-cli --root /source --dest /output --dry-run
```

### Common Options

```bash
# Filter by extension
mandala-cli --root /music --dest /playlist --extension .mp3 .flac

# Exclude keywords
mandala-cli --root /photos --dest /album --exclude vacation draft

# Random file count between 5-15
mandala-cli --root /source --dest /output --rand-min 5 --rand-max 15

# Limit file size (in MB)
mandala-cli --root /videos --dest /output --min-size 10 --max-size 500
```

### Transfer Modes

```bash
# Copy files (default)
mandala-cli --root /source --dest /output --mode copy

# Move files
mandala-cli --root /source --dest /output --mode move

# Create symbolic links
mandala-cli --root /source --dest /output --mode symlink

# Create hard links
mandala-cli --root /source --dest /output --mode hardlink
```

### Diversity Controls

```bash
# Maximum files per source folder
mandala-cli --root /source --dest /output --max-per-folder 2

# Ensure unique folder selection
mandala-cli --root /source --dest /output --unique-folders
```

## Graphical User Interface

### Launch GUI

```bash
mandala-gui
```

Or simply:

```bash
mandala
```

### GUI Features

1. **Configuration Tab**: Set source, destination, and file count
2. **Filters Tab**: Configure extension, keyword, size, and duration filters
3. **Advanced Tab**: Set diversity quotas and transfer modes
4. **Progress Tab**: Monitor transfer progress and view logs

### Profiles

Save frequently used configurations as profiles:

1. Configure settings in the GUI
2. Click **File → Save Profile**
3. Name your profile (e.g., "music_copy")
4. Load later with **File → Load Profile**

## Configuration File

Create a `mandala.json` file for reusable configurations:

```json
{
  "root": "/path/to/source",
  "dest": "/path/to/output",
  "filecount": {
    "count": 10,
    "rand_enabled": false,
    "rand_min": 0,
    "rand_max": 0
  },
  "extension": {
    "include_enabled": true,
    "exclude_enabled": false,
    "text": [".mp3", ".flac"]
  },
  "transfermode": {
    "transfer_mode": "Copy",
    "dry_run_enabled": false
  }
}
```

## Common Workflows

### Random Music Playlist

```bash
mandala-cli \
  --root ~/Music \
  --dest ~/Playlists/Random \
  --extension .mp3 .flac .m4a \
  --count 50 \
  --max-per-folder 2
```

### Photo Gallery Selection

```bash
mandala-cli \
  --root ~/Photos \
  --dest ~/Gallery \
  --extension .jpg .png \
  --min-size 1 \
  --exclude thumbnail draft \
  --count 20
```

### Video Highlights

```bash
mandala-cli \
  --root ~/Videos \
  --dest ~/Highlights \
  --extension .mp4 \
  --min-duration 30 \
  --max-duration 600 \
  --count 10
```

### Safe Preview (Dry Run)

```bash
mandala-cli \
  --root /important/files \
  --dest /backup \
  --dry-run \
  --count 100
```

## Advanced Features

### Custom Filename Templates

Use template variables in filenames:

- `{original}`: Original filename
- `{index}`: Sequential number
- `{date}`: Current date (YYYY-MM-DD)
- `{time}`: Current time (HH-MM-SS)
- `{datetime}`: Combined date and time
- `{parent}`: Parent folder name
- `{parentstoroot}`: Full parent path

Example: `{date}_{index}_{original}` → `2026-01-25_001_photo.jpg`

### Logging

Configure logging levels in `logging.json`:

```json
{
  "version": 1,
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "INFO"
    },
    "file": {
      "class": "logging.FileHandler",
      "filename": "mandala.log",
      "level": "DEBUG"
    }
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
- Use symlink or copy instead

**Duration filter not working:**
- Requires ffmpeg installed on system
- Only works with media files (video/audio)
- Check file format is supported by ffmpeg

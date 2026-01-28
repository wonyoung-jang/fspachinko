---
icon: lucide/code
---

# Development

Contributing to Mandala development.

## Setup Development Environment

### Prerequisites

- Python 3.14+
- uv package manager
- Git

### Clone and Install

```bash
# Clone repository
git clone https://github.com/wonyoung-jang/mandala.git
cd mandala

# Install with development dependencies
uv sync
```

## Project Structure

```
mandala/
├── mandala/
│   ├── core/          # Core engine logic
│   ├── config/        # Configuration management
│   ├── cli/           # Command-line interface
│   ├── gui/           # Graphical interface
│   └── utils/         # Shared utilities
├── mandala_config/    # Default configuration files
├── docs/              # Documentation (Zensical)
├── icons/             # Application icons
└── tests/             # Unit tests (future)
```

## Code Quality Tools

### Formatting and Linting

```bash
# Format code (120-char line length)
ruff format

# Lint and auto-fix
ruff check --fix --unsafe-fixes

# Type checking (Python 3.14 target)
ty check

# Dead code detection
uv run vulture
```

**Run all checks before committing:**

```bash
ruff format && ruff check --fix --unsafe-fixes && ty check && uv run vulture
```

### Linting Configuration

**ruff** ([ruff.toml](https://github.com/wonyoung-jang/mandala/blob/main/ruff.toml)):
- 120-character line length
- E4/E7/E9/F rules enabled
- Ignores: T201 (print allowed), S (security), D203/D213 (docstring style)

**vulture** ([pyproject.toml](https://github.com/wonyoung-jang/mandala/blob/main/pyproject.toml)):
- `min_confidence=40`
- Excludes `@app.*` decorators

**ty** ([ty.toml](https://github.com/wonyoung-jang/mandala/blob/main/ty.toml)):
- Targets Python 3.14

## Coding Standards

### Dataclasses with Slots

Use `@dataclass(slots=True)` for memory efficiency:

```python
from dataclasses import dataclass

@dataclass(slots=True)
class MyClass:
    field1: str
    field2: int
```

### Type Hints

Always provide type hints:

```python
def process_file(path: Path, size: int) -> bool:
    """Check if file meets criteria."""
    ...
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `FileValidator`, `MandalaEngine`)
- **Functions**: `snake_case` (e.g., `build_engine`, `process_folder`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `WALKER_CACHE_LIMIT`)
- **Private**: Prefix with `_` (e.g., `_get_duration`)

### Configuration Models

- Pydantic models: `*Model` suffix (e.g., `FilecountModel`)
- Dataclasses: Descriptive names (e.g., `Filecount`)

## Architecture Guidelines

### Observer Pattern

All UI updates must go through `MandalaObserver` callbacks:

```python
class MyObserver(MandalaObserver):
    def on_log(self, msg: str) -> None:
        print(msg)
    
    def on_progress(self, maximum: int) -> None:
        self.progressbar.setMaximum(maximum)
```

**Never** modify core logic to directly update UI elements.

### Core Layer Isolation

The core engine must remain UI-agnostic:
- No Qt imports in `mandala/core/`
- No print statements (use observer callbacks)
- No GUI-specific logic

### Path Handling

Always use `os.path` module over Pathlib.

### Thread Safety (GUI)

Qt operations must run in appropriate threads:
- Main thread: UI rendering and event handling
- Worker thread: Engine execution
- Use signals/slots for thread communication

```python
# Good - worker thread
class EngineWorker(QThread):
    def run(self) -> None:
        self.engine.start()

# Bad - blocks main thread
def on_start(self) -> None:
    self.engine.start()  # Never call directly in UI handler
```

## Adding New Features

### New Filter Type

Add to `FileValidator._validate()` in [validator.py](https://github.com/wonyoung-jang/mandala/blob/main/mandala/core/validator.py):

```python
@dataclass(slots=True)
class FileValidator:
    # Add new filter field
    new_filter: MyFilter
    
    def is_valid(self, path: Path, size: int) -> bool:
        # Add validation logic
        if not self.new_filter.is_valid(path):
            return False
        ...
```

### New Transfer Mode

1. Add enum to [constants.py](https://github.com/wonyoung-jang/mandala/blob/main/mandala/utils/constants.py):

```python
class TransferMode(StrEnum):
    COPY = "Copy"
    MOVE = "Move"
    SYMLINK = "Symlink"
    HARDLINK = "Hardlink"
    NEWTHING = "NewThing"  # Add here
```

2. Implement strategy in [transfer.py](https://github.com/wonyoung-jang/mandala/blob/main/mandala/core/transfer.py):

```python
def newthing_transfer(src: Path, dst: Path) -> None:
    """Implement new transfer logic."""
    ...

def fetch_transfer_strategy(mode: TransferMode) -> Callable[[Path, Path], None]:
    match mode:
        case TransferMode.NEWTHING:
            return newthing_transfer
        ...
```

### New Config Option

1. Add Pydantic model to [schemas.py](https://github.com/wonyoung-jang/mandala/blob/main/mandala/config/schemas.py):

```python
class NewFeatureModel(BaseModel):
    enabled: bool = False
    value: int = 0
```

2. Add to `MandalaConfigModel`:

```python
class MandalaConfigModel(BaseModel):
    ...
    newfeature: NewFeatureModel
```

3. Create dataclass in [config.py](https://github.com/wonyoung-jang/mandala/blob/main/mandala/config/config.py):

```python
@dataclass(slots=True)
class NewFeature:
    enabled: bool
    value: int
```

4. Wire in [builder.py](https://github.com/wonyoung-jang/mandala/blob/main/mandala/core/builder.py):

```python
def build_engine(m: MandalaConfigModel) -> MandalaEngine:
    newfeature = NewFeature(
        enabled=m.newfeature.enabled,
        value=m.newfeature.value,
    )
    ...
```

### New GUI Widget

Add to `MandalaCentralGui` in [centralwidget.py](https://github.com/wonyoung-jang/mandala/blob/main/mandala/gui/centralwidget.py):

```python
@dataclass(slots=True)
class MandalaCentralGui(QWidget):
    def __post_init__(self) -> None:
        super().__init__()
        
        # Add widget to UI
        self.my_widget = MyNewWidget()
        layout.addWidget(self.my_widget)
```

## Building Documentation

### Using Zensical

```bash
# Serve locally
zensical serve

# Build static site
zensical build

# Deploy (if configured)
zensical deploy
```

### Documentation Standards

- One file per module
- Use mkdocstrings syntax: `::: module.name`
- Include brief description before auto-generated docs
- Add usage examples where helpful

## Testing

### Manual Testing Checklist

- [ ] CLI runs without errors
- [ ] GUI launches and displays correctly
- [ ] File transfers work for all modes
- [ ] Filters correctly include/exclude files
- [ ] Dry run mode doesn't transfer files
- [ ] Reports generate successfully
- [ ] Progress tracking updates correctly

### Future: Unit Tests

(Planned)

```bash
# Run tests
pytest

# With coverage
pytest --cov=mandala
```

## Building Standalone Executables

### Using PyInstaller

```bash
# Build CLI executable
pyinstaller _gui.spec

# Output in dist/ directory
```

## Common Pitfalls

1. **Modifying core without observer**: All UI updates must go through callbacks
2. **JSON schema sync**: Update Pydantic models, dataclasses, and `mandala.json` together
3. **Path handling**: Use `Path` objects, avoid string manipulation
4. **Qt threading**: Never block main thread with `engine.start()`
5. **Stylesheet modifications**: Edit `style.qss`, avoid inline `setStyleSheet()`

## Debugging Tips

### Enable Debug Logging

Edit [logging.json](https://github.com/wonyoung-jang/mandala/blob/main/mandala_config/logging.json):

```json
{
  "handlers": {
    "console": {
      "level": "DEBUG"
    }
  }
}
```

### Profile Performance

```bash
# Install line_profiler
uv add line-profiler --group dev

# Profile specific functions
uv run python -m line_profiler mandala.prof
```

### Qt Designer (Future)

For complex GUI layouts, consider using Qt Designer:
1. Design UI in Designer
2. Convert `.ui` to Python: `pyside6-uic input.ui -o output.py`
3. Import generated module

## Release Checklist

1. Update version in [pyproject.toml](https://github.com/wonyoung-jang/mandala/blob/main/pyproject.toml)
2. Run all code quality tools
3. Test CLI and GUI manually
4. Update CHANGELOG.md (if exists)
5. Build documentation: `zensical build`
6. Create git tag: `git tag v0.0.1`
7. Build executables with PyInstaller
8. Create GitHub release

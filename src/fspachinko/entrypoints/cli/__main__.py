"""Main entry point for CLI."""

from fspachinko.entrypoints.cli.app import app


def main() -> None:
    """Enter CLI."""
    app()


if __name__ == "__main__":
    main()

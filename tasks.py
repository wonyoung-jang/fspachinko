"""Tasks for development."""

import invoke
from invoke import task

# ruff: noqa: A001
# ruff: noqa: D103


# Linting and formatting
@task
def lint(c: invoke.Context) -> None:
    c.run("uv run ruff check --fix --unsafe-fixes")
    c.run("uv run ty check")


@task
def format(c: invoke.Context) -> None:
    c.run("uv run ruff format")


@task
def vulture(c: invoke.Context) -> None:
    c.run("uv run vulture")


@task(pre=[lint, format, vulture])
def clean(c: invoke.Context) -> None: ...


# Running
@task
def run(c: invoke.Context) -> None:
    c.run("uv run fspachinko")


@task
def cli(c: invoke.Context) -> None:
    c.run("uv run fspachinko-cli")


@task
def gui(c: invoke.Context) -> None:
    c.run("uv run fspachinko-gui")


@task
def lprof(c: invoke.Context, entry: str = "gui") -> None:
    c.run(f"uv run kernprof -lv -m fspachinko.entrypoints.{entry}")


@task
def cprof(c: invoke.Context, entry: str = "gui") -> None:
    c.run(f"uv run python -m cProfile -o fspachinko.prof -m fspachinko.entrypoints.{entry}")


@task
def snakeviz(c: invoke.Context) -> None:
    c.run("uv run -m snakeviz fspachinko.prof")


@task
def test(c: invoke.Context) -> None:
    c.run("uv run pytest")


@task
def testcov(c: invoke.Context) -> None:
    c.run("uv run pytest --cov=src/fspachinko --cov-report=html")


# Syncing
@task
def syncall(c: invoke.Context) -> None:
    c.run("uv sync --all-groups")


@task
def upgradelock(c: invoke.Context) -> None:
    c.run("uv lock -U")

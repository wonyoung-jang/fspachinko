"""Tasks for development."""

import invoke
from invoke import task

# ruff: noqa: A001
# ruff: noqa: D103


@task
def run(c: invoke.Context) -> None:
    c.run("uv run fspachinko")


@task
def lint(c: invoke.Context) -> None:
    c.run("uv run ruff check --fix")
    c.run("uv run ty check")


@task
def format(c: invoke.Context) -> None:
    c.run("uv run ruff format")


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


@task(pre=[lint, format, test])
def all(c: invoke.Context) -> None: ...

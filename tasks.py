"""Tasks for development."""

import invoke
from invoke import task


@task
def lint(c: invoke.Context) -> None:
    """Run ruff check with fixes."""
    c.run("uv run ruff check --fix")
    c.run("uv run ty check")


@task
def format(c: invoke.Context) -> None:  # noqa: A001
    """Format code with ruff."""
    c.run("uv run ruff format")


@task
def test(c: invoke.Context) -> None:
    """Run tests."""
    c.run("pytest")


@task(pre=[lint, format, test])
def all(c: invoke.Context) -> None:  # noqa: A001
    """Run all checks."""

"""Smoke tests for the CLI entrypoint."""

from click.testing import CliRunner

from aurmod.cli import cli


def test_help() -> None:
    """--help shows available commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0

    for command in cli.commands:
        assert command in result.output


def test_no_args() -> None:
    """Running with no argument shows help."""
    runner = CliRunner()
    result = runner.invoke(cli, [])

    # click exits 2 with no cmd
    assert result.exit_code == 2

    for command in cli.commands:
        assert command in result.output

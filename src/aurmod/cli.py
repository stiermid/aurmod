"""Command-line interference for aurmod."""

import click

from .commands.init import init


@click.group()
def cli():
    """aurmod - managing AUR packages using git submodules."""  # noqa: D403
    pass


cli.add_command(init)

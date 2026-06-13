"""Command-line interference for aurmod."""

import click

from .commands.add import add
from .commands.init import init
from .commands.sync import sync


@click.group()
def cli():
    """aurmod - managing AUR packages using git submodules."""  # noqa: D403
    pass


cli.add_command(init)
cli.add_command(add)
cli.add_command(sync)

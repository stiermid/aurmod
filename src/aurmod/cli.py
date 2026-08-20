"""Command-line interface for aurmod."""

import click

from .commands.add import add
from .commands.hooks import pre_commit, prepare_commit_msg
from .commands.setup import setup
from .commands.sync import sync
from .commands.update import update


@click.group()
def cli():
    """aurmod - managing AUR packages using git submodules."""  # noqa: D403
    pass


cli.add_command(add)
cli.add_command(pre_commit)
cli.add_command(prepare_commit_msg)
cli.add_command(setup)
cli.add_command(sync)
cli.add_command(update)

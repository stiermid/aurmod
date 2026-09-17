"""Command-line interference for aurmod."""

import click

from .commands.add import add
from .commands.check import check
from .commands.exec_cmd import exec_cmd
from .commands.init import init
from .commands.log import log
from .commands.pull import pull
from .commands.push import push
from .commands.status import status


@click.group()
def cli():
    """aurmod - managing AUR packages using git submodules."""  # noqa: D403
    pass


cli.add_command(add)
cli.add_command(check)
cli.add_command(exec_cmd)
cli.add_command(init)
cli.add_command(log)
cli.add_command(pull)
cli.add_command(push)
cli.add_command(status)

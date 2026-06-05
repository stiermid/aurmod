"""Initialize project resoruces.

This module provides the ``init`` CLI command.
"""

import click


@click.command()
def init():
    """Installs git hooks to the repo."""
    click.echo("init function tiggered")

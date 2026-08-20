"""Install aurmod git hooks into package submodules."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import click

from ..utils import get_root_repo

if TYPE_CHECKING:
    from git import Repo

HOOK_NAMES = ("pre-commit", "prepare-commit-msg")


def _hooks_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "hooks"


@click.command()
def setup() -> None:
    """Install aurmod hooks into package submodules."""
    repo = get_root_repo()

    modules = []
    for sm in repo.submodules:
        if not sm.module_exists():
            click.echo(
                f"Skipping {sm.name}: submodule is not checked out.", err=True
            )
            continue
        modules.append(sm.module())

    if not modules:
        raise click.ClickException("No submodules found to install hooks into.")

    for module in modules:
        _install_hooks(module)

    click.echo("Hooks installed. Commit inside a submodule to use them.")


def _install_hooks(repo: Repo) -> None:
    hooks_dir = Path(repo.git_dir) / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in HOOK_NAMES:
        target = hooks_dir / name
        if target.exists() and not _is_aurmod_hook(target):
            click.echo(
                f"Skipping {name}: an existing hook is present.", err=True
            )
            continue
        shutil.copy2(_hooks_dir() / name, target)
        target.chmod(0o755)
        click.echo(f"Installed {name}")


def _is_aurmod_hook(path: Path) -> bool:
    return "aurmod" in path.read_text(encoding="utf-8")

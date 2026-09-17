"""Prepare a collection once with sane submodule settings."""

from __future__ import annotations

import os
import stat
import subprocess

import click

from ..utils import get_root_repo

SETTINGS = {
    "submodule.recurse": "true",
    "push.recurseSubmodules": "check",
    "status.submoduleSummary": "true",
    "diff.submodule": "log",
}

SSH_SNIPPET = """Host aur.archlinux.org
  User aur
  HostName aur.archlinux.org
  IdentityFile ~/.ssh/aur
  IdentitiesOnly yes"""

PRE_COMMIT = """#!/bin/sh
# aurmod guard: commit package files inside the package folder.
staged=$(git diff --cached --name-only)
submodules=$(git config --file .gitmodules --get-regexp submodule \\
  2>/dev/null | awk '{print $2}')
blocked=0
for sm in $submodules; do
  echo "$staged" | grep -q "^$sm/" && {
    echo "aurmod: '$sm/' holds a package; commit inside '$sm' instead:" 1>&2
    echo "  cd $sm && git add <files> && git commit" 1>&2
    blocked=1
  }
done
exit $blocked
"""

PRE_PUSH = """#!/bin/sh
# aurmod guard: never push the outer collection to the AUR.
remote="$1"
url="$2"
case "$url" in
  *aur.archlinux.org*)
    if test -f .gitmodules; then
      echo "aurmod: refusing to push the outer collection to the AUR." 1>&2
      echo "Push a single package instead: aurmod push <name>" 1>&2
      exit 1
    fi
    ;;
esac
exit 0
"""


def _write_hook(repo_dir: str, name: str, content: str) -> str:
    """Write an executable hook file and return its path."""
    path = os.path.join(repo_dir, ".git", "hooks", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _check_ssh() -> bool:
    """Return ``True`` when authenticated SSH to the AUR works."""
    try:
        proc = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                "-T",
                "aur@aur.archlinux.org",
                "list-repos",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError, subprocess.TimeoutExpired:
        return False
    return proc.returncode == 0


@click.command()
def init() -> None:
    """Prepare the collection: configs, guards and an SSH check."""
    repo = get_root_repo()
    assert repo.working_tree_dir is not None
    root = str(repo.working_tree_dir)

    with repo.config_writer() as writer:
        for key, value in SETTINGS.items():
            section, _, option = key.partition(".")
            writer.set_value(section, option, value)

    _write_hook(root, "pre-commit", PRE_COMMIT)
    _write_hook(root, "pre-push", PRE_PUSH)
    click.echo("Configured submodule behavior and installed git guards.")

    if _check_ssh():
        click.echo("SSH to aur.archlinux.org works.")
    else:
        click.echo("SSH to aur.archlinux.org failed.")
        click.echo("Add a key to https://aur.archlinux.org/account, then:")
        click.echo("")
        click.echo(SSH_SNIPPET)
        click.echo("")
        click.echo("Test with: ssh -T aur@aur.archlinux.org help")

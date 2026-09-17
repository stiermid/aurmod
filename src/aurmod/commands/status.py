"""Show one line per package with version and sync state."""

from __future__ import annotations

from pathlib import Path

import click

from ..pkg import get_version, srcinfo_status
from ..utils import (
    ahead_behind,
    fetch_origin,
    get_root_repo,
    pointer_state,
    require_submodules,
)


@click.command()
def status() -> None:
    """Show version, dirtiness, SRCINFO, ahead/behind and pointer."""
    repo = get_root_repo()
    assert repo.working_tree_dir is not None
    root = str(repo.working_tree_dir)
    sms = require_submodules(repo)
    for sm in sorted(sms, key=lambda s: s.name):
        pkg_dir = Path(root) / sm.path
        version = get_version(pkg_dir)
        try:
            sm_repo = sm.module() if sm.module_exists() else None
        except ValueError:
            sm_repo = None
        dirty = "?"
        if sm_repo is not None:
            dirty = (
                "dirty" if sm_repo.is_dirty(untracked_files=True) else "clean"
            )
        state, _ = srcinfo_status(pkg_dir)
        srcinfo = {
            "ok": "srcinfo-ok",
            "stale": "srcinfo-stale",
            "missing": "srcinfo-missing",
            "error": "srcinfo-?",
        }.get(state, "srcinfo-?")

        if sm_repo is None:
            sync = "not-initialized"
        else:
            fetch_origin(sm_repo)
            ahead, behind = ahead_behind(sm_repo)
            if ahead is None:
                sync = "no-upstream"
            else:
                sync = f"ahead{ahead} behind{behind}"

        pointer = pointer_state(repo, sm)["state"]
        pointer_txt = {
            "ok": "pointer-ok",
            "staged": "pointer-staged",
            "outdated": "pointer-outdated",
            "unknown": "pointer-?",
        }.get(str(pointer), "pointer-?")
        click.echo(
            f"{sm.name} {version} {dirty} {srcinfo} {sync} {pointer_txt}"
        )

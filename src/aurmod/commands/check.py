"""Report publish blockers for packages in plain language."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import click

from ..pkg import REGENERATE_MSG, get_pkgbase, srcinfo_status
from ..utils import (
    get_root_repo,
    get_submodule,
    require_submodules,
    whitespace_issues,
)


def check_one(root: str, name: str) -> list[str]:
    """Return a list of human-readable issues for one package."""
    repo = get_root_repo(root)
    sm = get_submodule(repo, name)
    assert repo.working_tree_dir is not None
    pkg_dir = Path(repo.working_tree_dir) / sm.path
    issues: list[str] = []

    pkgbuild = pkg_dir / "PKGBUILD"
    srcinfo = pkg_dir / ".SRCINFO"
    if not pkgbuild.is_file():
        issues.append("missing PKGBUILD")
    if not srcinfo.is_file():
        issues.append("missing .SRCINFO")

    if srcinfo.is_file():
        base = get_pkgbase(pkg_dir)
        if base is None:
            issues.append("cannot read pkgbase from .SRCINFO")
        elif base != name:
            issues.append(
                f"folder {name!r} does not match pkgbase {base!r}; "
                f"rename the folder to {base!r}"
            )

        state, detail = srcinfo_status(pkg_dir)
        if state == "stale":
            issues.append(f".SRCINFO is stale; run: {REGENERATE_MSG}")
        elif state == "error":
            issues.append(f"cannot verify .SRCINFO: {detail}")

    if pkgbuild.is_file():
        proc = subprocess.run(
            ["bash", "-n", str(pkgbuild)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            err = (proc.stderr or "syntax error").strip()
            issues.append(f"PKGBUILD syntax error: {err}")

    try:
        if sm.module_exists():
            problems = whitespace_issues(sm.module())
            if problems:
                issues.append(f"whitespace errors:\n{problems}")
    except ValueError:
        issues.append("submodule is not initialized")

    pkgbuild_path = pkg_dir / "PKGBUILD"
    if pkgbuild_path.is_file() and shutil.which("namcap"):
        proc = subprocess.run(
            ["namcap", str(pkgbuild_path)],
            capture_output=True,
            text=True,
        )
        out = f"{proc.stdout or ''}\n{proc.stderr or ''}".strip()
        # namcap prints warnings even on clean files; only
        # surface lines mentioning errors or warnings.
        interesting = [
            line
            for line in out.splitlines()
            if "error" in line.lower() or "warning" in line.lower()
        ]
        if interesting:
            issues.append("namcap PKGBUILD: " + "; ".join(interesting))

    return issues


@click.command()
@click.argument("pkgname", required=False, default=None)
@click.option(
    "--all",
    "all_packages",
    is_flag=True,
    help="Check every package in the collection.",
)
def check(pkgname: str | None, all_packages: bool) -> None:
    """Report missing files, stale .SRCINFO and packaging issues."""
    repo = get_root_repo()
    if all_packages:
        names = [sm.name for sm in require_submodules(repo)]
    elif pkgname:
        names = [get_submodule(repo, pkgname).name]
    else:
        raise click.ClickException("Specify a package or use --all.")

    assert repo.working_tree_dir is not None
    root = str(repo.working_tree_dir)
    failed: list[str] = []
    for name in sorted(names):
        issues = check_one(root, name)
        if not issues:
            click.echo(f"{name}: OK")
        else:
            failed.append(name)
            click.echo(f"{name}:")
            for issue in issues:
                click.echo(f"  - {issue}")
    if failed:
        raise click.ClickException(
            f"Check failed for: {', '.join(sorted(failed))}"
        )

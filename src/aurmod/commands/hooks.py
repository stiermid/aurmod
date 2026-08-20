"""Internal commands backing the bundled git hooks."""

from __future__ import annotations

import os
from pathlib import Path

import click
from git import InvalidGitRepositoryError, Repo

from ..checks import IntegrityError, print_srcinfo_dir, verify_package
from ..messages import describe_package, parse_srcinfo, parse_srcinfo_file


def _current_repo() -> Repo:
    try:
        return Repo(".")
    except InvalidGitRepositoryError:
        raise click.ClickException("Git repo is not found.")


@click.command(hidden=True, name="pre-commit")
def pre_commit() -> None:
    """Verify staged package changes (git pre-commit hook)."""
    repo = _current_repo()
    try:
        verify_package(repo)
    except IntegrityError as e:
        raise click.ClickException(str(e))


@click.command(hidden=True, name="prepare-commit-msg")
@click.argument("msgfile")
def prepare_commit_msg(msgfile: str) -> None:
    """Pre-fill a commit message with package changes (git hook)."""
    repo = _current_repo()
    wd = Path(repo.working_tree_dir)

    lines = []
    for diff_filter, action in (("A", "Initial upload"), ("M", "upgpkg")):
        paths = repo.git.diff(
            "--cached", "--name-only", f"--diff-filter={diff_filter}"
        ).splitlines()
        for path in paths:
            if not path.endswith("PKGBUILD"):
                continue
            pkg_dir = wd / os.path.dirname(path)
            info = _package_info(pkg_dir)
            pkgname = _pkgname(wd, pkg_dir)
            lines.append(f"{action}: {describe_package(pkgname, info)}")

    for path in repo.git.diff(
        "--cached", "--name-only", "--diff-filter=D"
    ).splitlines():
        if path.endswith("PKGBUILD"):
            pkg_dir = wd / os.path.dirname(path)
            lines.append(f"Deleted package: {_pkgname(wd, pkg_dir)}")

    if not lines:
        return

    msg_path = Path(msgfile)
    original = msg_path.read_text(encoding="utf-8")
    content = "\n".join(lines)
    if original.strip():
        content += f"\n\n{original}"
    msg_path.write_text(content, encoding="utf-8")


def _package_info(pkg_dir: Path) -> dict[str, str] | None:
    fresh = print_srcinfo_dir(pkg_dir)
    if fresh is not None:
        (pkg_dir / ".SRCINFO").write_text(fresh, encoding="utf-8")
        return parse_srcinfo(fresh)
    return parse_srcinfo_file(pkg_dir / ".SRCINFO")


def _pkgname(wd: Path, pkg_dir: Path) -> str:
    return pkg_dir.name if pkg_dir != wd else wd.name

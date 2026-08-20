"""Commit message generation from package metadata."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git import Repo

_LINE_RE = re.compile(r"^\s*(\w+)\s*=\s*(.+?)\s*$")


def parse_srcinfo(text: str) -> dict[str, str]:
    """Parse ``.SRCINFO`` content into the first value per key."""
    info: dict[str, str] = {}
    for line in text.splitlines():
        match = _LINE_RE.match(line)
        if match:
            key, value = match.groups()
            info.setdefault(key, value)
    return info


def parse_srcinfo_file(path: Path) -> dict[str, str] | None:
    """Parse the ``.SRCINFO`` file at *path*, or ``None`` if missing."""
    if not path.is_file():
        return None
    return parse_srcinfo(path.read_text(encoding="utf-8"))


def read_srcinfo(repo: Repo) -> dict[str, str] | None:
    """Read the package ``.SRCINFO`` from a repository's working tree."""
    return parse_srcinfo_file(Path(repo.working_tree_dir) / ".SRCINFO")


def version_str(info: dict[str, str]) -> str:
    """Format ``epoch:pkgver-pkgrel`` from parsed ``.SRCINFO``."""
    epoch = info.get("epoch")
    prefix = f"{epoch}:" if epoch else ""
    return f"{prefix}{info.get('pkgver', '')}-{info.get('pkgrel', '')}"


def describe_package(pkgname: str, info: dict[str, str] | None) -> str:
    """Describe a package, e.g. ``pkg-a`` or ``pkg-a 2.0-1``."""
    if info is None:
        return pkgname
    return f"{pkgname} {version_str(info)}"

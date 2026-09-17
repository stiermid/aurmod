"""Helpers for reading and validating AUR package folders."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git.types import PathLike

AUR_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9@._+\-]*$")

REGENERATE_MSG = "makepkg --printsrcinfo > .SRCINFO"


def parse_srcinfo(text: str) -> dict[str, object]:
    """Parse ``.SRCINFO`` content into pkgbase, pkgnames and version."""
    pkgbase: str | None = None
    pkgnames: list[str] = []
    pkgver: str | None = None
    pkgrel: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("pkgbase ="):
            pkgbase = line.split("=", 1)[1].strip()
        elif line.startswith("pkgname ="):
            pkgnames.append(line.split("=", 1)[1].strip())
        elif line.startswith("pkgver =") and pkgver is None:
            pkgver = line.split("=", 1)[1].strip()
        elif line.startswith("pkgrel =") and pkgrel is None:
            pkgrel = line.split("=", 1)[1].strip()
    if pkgbase is None and pkgnames:
        pkgbase = pkgnames[0]
    return {
        "pkgbase": pkgbase,
        "pkgnames": pkgnames,
        "pkgver": pkgver,
        "pkgrel": pkgrel,
    }


def read_srcinfo(pkg_dir: PathLike) -> str | None:
    """Return the raw ``.SRCINFO`` content, or ``None`` if missing."""
    path = Path(str(pkg_dir)) / ".SRCINFO"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def get_pkgbase(pkg_dir: PathLike) -> str | None:
    """Return the package base name from ``.SRCINFO``."""
    text = read_srcinfo(pkg_dir)
    if text is None:
        return None
    result = parse_srcinfo(text)
    base = result["pkgbase"]
    return str(base) if isinstance(base, str) else None


def get_version(pkg_dir: PathLike) -> str:
    """Return ``pkgver-pkgrel`` from ``.SRCINFO`` or ``unknown``."""
    text = read_srcinfo(pkg_dir)
    if text is None:
        return "unknown"
    result = parse_srcinfo(text)
    ver = result["pkgver"]
    rel = result["pkgrel"]
    if isinstance(ver, str) and isinstance(rel, str):
        return f"{ver}-{rel}"
    return "unknown"


def run_printsrcinfo(pkg_dir: PathLike) -> tuple[str | None, str | None]:
    """Run ``makepkg --printsrcinfo`` inside the package directory.

    Returns a ``(output, error)`` tuple. ``output`` is ``None`` when
    makepkg failed or is not installed; ``error`` holds the detail.
    """
    try:
        proc = subprocess.run(
            ["makepkg", "--printsrcinfo"],
            cwd=str(pkg_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return None, "makepkg not found"
    except subprocess.TimeoutExpired:
        return None, "makepkg timed out"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "makepkg failed").strip()
        return None, err
    return proc.stdout, None


def srcinfo_status(pkg_dir: PathLike) -> tuple[str, str | None]:
    """Compare ``.SRCINFO`` against ``makepkg --printsrcinfo``.

    Returns ``(state, detail)`` where state is one of ``ok``,
    ``stale``, ``missing`` or ``error``.
    """
    current = read_srcinfo(pkg_dir)
    if current is None:
        return "missing", None
    generated, error = run_printsrcinfo(pkg_dir)
    if generated is None:
        return "error", error
    if generated.strip() == current.strip():
        return "ok", None
    return "stale", None


def is_valid_aur_name(name: str) -> bool:
    """Check whether a name is a valid AUR package name."""
    return bool(AUR_NAME_RE.match(name))


def pkgbuild_template(pkgname: str) -> str:
    """Return a minimal ``PKGBUILD`` template for a new package."""
    return f"""# Maintainer: Your Name <you@example.com>
pkgname={pkgname}
pkgver=0.1
pkgrel=1
pkgdesc="A short description of {pkgname}"
arch=('any')
url="https://example.com"
license=('GPL-3.0-or-later')
source=()
sha256sums=()

package() {{
  :
}}
"""


def srcinfo_template(pkgname: str) -> str:
    """Return a minimal ``.SRCINFO`` matching the template above."""
    return f"""pkgbase = {pkgname}
\tpkgdesc = A short description of {pkgname}
\tpkgver = 0.1
\tpkgrel = 1
\turl = https://example.com
\tarch = any
\tlicense = GPL-3.0-or-later

pkgname = {pkgname}
"""

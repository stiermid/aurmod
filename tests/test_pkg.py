"""Tests for :mod:`aurmod.pkg`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aurmod.pkg import (
    REGENERATE_MSG,
    get_pkgbase,
    get_version,
    is_valid_aur_name,
    parse_srcinfo,
    pkgbuild_template,
    srcinfo_status,
    srcinfo_template,
)

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE = """pkgbase = foo
\tpkgdesc = test
\tpkgver = 1.0
\tpkgrel = 2
\turl = https://example.com
\tarch = any
\tlicense = MIT

pkgname = foo
"""


def test_parse_srcinfo() -> None:
    """pkgbase, version and names are extracted."""
    result = parse_srcinfo(SAMPLE)
    assert result["pkgbase"] == "foo"
    assert result["pkgver"] == "1.0"
    assert result["pkgrel"] == "2"
    assert result["pkgnames"] == ["foo"]


def test_parse_srcinfo_falls_back_to_pkgname() -> None:
    """Without pkgbase the first pkgname is the base."""
    result = parse_srcinfo("pkgname = bar\npkgver = 0.1\npkgrel = 1\n")
    assert result["pkgbase"] == "bar"


def test_get_pkgbase_and_version(tmp_path: Path) -> None:
    """Helpers read .SRCINFO from a package directory."""
    (tmp_path / ".SRCINFO").write_text(SAMPLE, encoding="utf-8")
    assert get_pkgbase(tmp_path) == "foo"
    assert get_version(tmp_path) == "1.0-2"


def test_get_version_unknown(tmp_path: Path) -> None:
    """Missing .SRCINFO yields unknown version."""
    assert get_version(tmp_path) == "unknown"
    assert get_pkgbase(tmp_path) is None


def test_valid_names() -> None:
    """AUR name validation accepts normal names and rejects bad ones."""
    assert is_valid_aur_name("foo") is True
    assert is_valid_aur_name("foo-bar_git") is True
    assert is_valid_aur_name("Foo") is False
    assert is_valid_aur_name("foo bar") is False
    assert is_valid_aur_name("") is False


def test_templates_match() -> None:
    """The offline templates agree on pkgbase."""
    pkgbuild = pkgbuild_template("my-pkg")
    srcinfo = srcinfo_template("my-pkg")
    assert "pkgname=my-pkg" in pkgbuild
    assert parse_srcinfo(srcinfo)["pkgbase"] == "my-pkg"


def test_srcinfo_missing(tmp_path: Path) -> None:
    """Missing .SRCINFO is reported distinctly."""
    state, _ = srcinfo_status(tmp_path)
    assert state == "missing"


def test_srcinfo_ok_and_stale(tmp_path: Path, monkeypatch) -> None:
    """Stale detection compares makepkg output against the file."""
    import aurmod.pkg as pkg_mod

    (tmp_path / ".SRCINFO").write_text(SAMPLE, encoding="utf-8")
    monkeypatch.setattr(pkg_mod, "run_printsrcinfo", lambda _d: (SAMPLE, None))
    assert srcinfo_status(tmp_path)[0] == "ok"

    monkeypatch.setattr(
        pkg_mod, "run_printsrcinfo", lambda _d: (SAMPLE + "\n", None)
    )
    state, _ = srcinfo_status(tmp_path)
    # trailing newline is normalized, so still ok; change content instead.
    assert state == "ok"

    monkeypatch.setattr(
        pkg_mod, "run_printsrcinfo", lambda _d: ("pkgbase = other\n", None)
    )
    assert srcinfo_status(tmp_path)[0] == "stale"
    assert "printsrcinfo" in REGENERATE_MSG

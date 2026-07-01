"""Tests for the /SNS read-only write guard."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.cp_bench import safety
from scripts.cp_bench.safety import ReadOnlyPathError, assert_writable, is_protected, safe_write_text


def test_sns_is_protected() -> None:
    assert is_protected("/SNS")
    assert is_protected("/SNS/TOPAZ/IPTS-1/nexus/TOPAZ_1.nxs.h5")
    assert not is_protected("/home/someone/IPTS-1/CP-bench")


def test_assert_writable_blocks_sns() -> None:
    with pytest.raises(ReadOnlyPathError):
        assert_writable("/SNS/TOPAZ/shared/out.txt")


def test_assert_writable_allows_tmp(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "file.txt"
    assert assert_writable(target) == os.path.realpath(str(target))


def test_safe_write_text_under_tmp(tmp_path: Path) -> None:
    path = safe_write_text(str(tmp_path / "a" / "b.txt"), "hello")
    assert Path(path).read_text() == "hello"


def test_safe_write_text_blocks_sns() -> None:
    with pytest.raises(ReadOnlyPathError):
        safe_write_text("/SNS/TOPAZ/evil.txt", "nope")


def test_symlink_cannot_escape_into_sns(tmp_path: Path) -> None:
    link = tmp_path / "escape"
    os.symlink("/SNS/TOPAZ", link)  # target need not exist to resolve
    with pytest.raises(ReadOnlyPathError):
        assert_writable(link / "out.txt")


def test_env_can_add_but_not_remove_default_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    extra = tmp_path / "readonly"
    monkeypatch.setenv("CP_BENCH_READONLY_ROOTS", str(extra))
    roots = safety.readonly_roots()
    assert os.path.realpath("/SNS") in roots
    assert os.path.realpath(str(extra)) in roots
    with pytest.raises(ReadOnlyPathError):
        assert_writable(extra / "x.txt")

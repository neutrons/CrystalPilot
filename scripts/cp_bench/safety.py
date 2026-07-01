"""Read-only guard for protected filesystem roots (``/SNS`` by default).

Every filesystem *write* in CP-Bench must go through the helpers in this
module. Reads are never intercepted — the harness must read NeXus files and
reduction configs from ``/SNS``. Writes are resolved to a real path (following
symlinks) and refused if they land on or under a protected root, so a symlink
inside the output tree cannot be used to escape into ``/SNS``.

Protected roots default to ``("/SNS",)`` and can be extended (never reduced
below the default) via the ``CP_BENCH_READONLY_ROOTS`` environment variable
(``os.pathsep``-separated).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO, Any, Iterable

#: Roots that must never be written to. The default is always included; the
#: environment can only *add* to this set, never remove ``/SNS``.
DEFAULT_READONLY_ROOTS: tuple[str, ...] = ("/SNS",)

_ENV_VAR = "CP_BENCH_READONLY_ROOTS"


class ReadOnlyPathError(RuntimeError):
    """Raised when a write is attempted on or under a protected (read-only) root."""


def _resolve(path: str | os.PathLike[str]) -> str:
    """Return the fully resolved absolute path (user- and symlink-expanded)."""
    return os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(path))))


def readonly_roots() -> tuple[str, ...]:
    """Return the protected roots: the built-in default plus any from the env."""
    roots = list(DEFAULT_READONLY_ROOTS)
    extra = os.environ.get(_ENV_VAR, "")
    for token in extra.split(os.pathsep):
        token = token.strip()
        if token:
            roots.append(token)
    # Resolve + de-duplicate while preserving order.
    seen: set[str] = set()
    resolved: list[str] = []
    for root in roots:
        real = _resolve(root)
        if real not in seen:
            seen.add(real)
            resolved.append(real)
    return tuple(resolved)


def _is_within(child: str, parent: str) -> bool:
    """True if ``child`` is ``parent`` itself or nested under it."""
    if child == parent:
        return True
    return child.startswith(parent.rstrip(os.sep) + os.sep)


def is_protected(path: str | os.PathLike[str], roots: Iterable[str] | None = None) -> bool:
    """Return True if writing to ``path`` would touch a protected root."""
    real = _resolve(path)
    check_roots = tuple(roots) if roots is not None else readonly_roots()
    return any(_is_within(real, root) for root in check_roots)


def assert_writable(path: str | os.PathLike[str]) -> str:
    """Return the resolved path, or raise :class:`ReadOnlyPathError` if protected."""
    real = _resolve(path)
    for root in readonly_roots():
        if _is_within(real, root):
            raise ReadOnlyPathError(
                f"Refusing to write under read-only root {root!r}: {os.fspath(path)!r} "
                f"(resolves to {real!r}). CP-Bench never modifies {root}."
            )
    return real


def safe_makedirs(path: str | os.PathLike[str], exist_ok: bool = True) -> str:
    """``mkdir -p`` after asserting the target is writable; returns the resolved path."""
    real = assert_writable(path)
    os.makedirs(real, exist_ok=exist_ok)
    return real


def safe_open(path: str | os.PathLike[str], mode: str = "r", **kwargs: Any) -> IO[Any]:
    """Open a file; any write/append/update mode is refused under a protected root."""
    if any(flag in mode for flag in ("w", "a", "x", "+")):
        assert_writable(path)
    return open(path, mode, **kwargs)


def safe_write_text(path: str | os.PathLike[str], text: str, encoding: str = "utf-8") -> str:
    """Write text to ``path`` (creating parents) after the read-only check."""
    real = assert_writable(path)
    safe_makedirs(os.path.dirname(real) or ".")
    Path(real).write_text(text, encoding=encoding)
    return real


def safe_write_bytes(path: str | os.PathLike[str], data: bytes) -> str:
    """Write bytes to ``path`` (creating parents) after the read-only check."""
    real = assert_writable(path)
    safe_makedirs(os.path.dirname(real) or ".")
    Path(real).write_bytes(data)
    return real


def guard_output_root(path: str | os.PathLike[str]) -> str:
    """Validate a chosen output root at startup; returns the resolved path.

    Fails fast if the benchmark's output directory would resolve under a
    protected root — a misconfiguration that must never proceed.
    """
    return assert_writable(path)

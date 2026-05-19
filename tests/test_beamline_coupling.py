"""Beamline-coupling regression ratchet.

The multi-beamline refactor reduced hardcoded TOPAZ/BL12 references in the
framework-side code (``src/exphub/app/``, ``src/exphub/agent/``,
``src/exphub/core/``) to zero. Any TOPAZ/BL12 string that survives must
live inside a beamline plug-in directory (``src/exphub/beamlines/``) or
the explicit allow-list below.

This test guards against accidental re-introduction.

History: started 2026-05-19 with 235 occurrences across 17 files. See
``MULTI_BEAMLINE_PLAN.md`` for the phase-by-phase shrink.
"""

from __future__ import annotations

import re
from pathlib import Path

PATTERN = re.compile(r"TOPAZ|BL12|topaz|bl12")

# Directories where hardcoded beamline ids are LEGITIMATE.
ALLOWED_PREFIXES = (
    "src/exphub/beamlines/",
    "tests/",
)

# Individual files that legitimately mention beamline ids — docstring
# examples inside framework code, vendored clients with multi-beamline
# lookup tables. Prefer ``ALLOWED_PREFIXES``.
ALLOWED_FILES = {
    "src/exphub/core/beamline/spec.py",
    # Vendored EIC client — owns a name-normalizer table for every SNS beamline.
    "src/exphub/app/models/eic_client.py",
}

REPO_ROOT = Path(__file__).resolve().parent.parent


def _count_matches(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return len(PATTERN.findall(text))


def _scan() -> dict[str, int]:
    counts: dict[str, int] = {}
    for py in (REPO_ROOT / "src").rglob("*.py"):
        rel = py.relative_to(REPO_ROOT).as_posix()
        if rel.startswith(ALLOWED_PREFIXES) or rel in ALLOWED_FILES:
            continue
        n = _count_matches(py)
        if n:
            counts[rel] = n
    return counts


def test_no_framework_side_beamline_coupling() -> None:
    """Fail if framework-side code (outside allow-listed paths) picks up
    a TOPAZ/BL12 hardcoded reference. Adding such a reference means either:
      - the code belongs under ``beamlines/<id>/`` (preferred), or
      - if it's a legitimate generic mention, add the file to ALLOWED_FILES.
    """
    counts = _scan()
    assert not counts, (
        "Hardcoded beamline ids found outside allow-list:\n"
        + "\n".join(f"  {n:5d}  {f}" for f, n in sorted(counts.items()))
        + "\n\nMove the constants into beamlines/<id>/ or add an "
        "ALLOWED_FILES exception."
    )

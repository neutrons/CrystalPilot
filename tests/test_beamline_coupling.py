"""Beamline-coupling regression ratchet.

Counts hardcoded TOPAZ/BL12 references per file and asserts they do not
exceed the recorded baseline. Each multi-beamline refactor phase should
*reduce* these numbers; the test fails if a file regresses (or if a new
file picks up hardcoded references).

When a phase legitimately reduces a file's count, lower the baseline
here. The eventual goal is zero entries outside ``beamlines/topaz/``.

See MULTI_BEAMLINE_PLAN.md (section "Phase 0").
"""

from __future__ import annotations

import re
from pathlib import Path

PATTERN = re.compile(r"TOPAZ|BL12|topaz|bl12")

# Recorded 2026-05-19 on branch ``multibeamline`` at Phase 0b.
# Counts are pattern *occurrences* (re.findall), not lines.
# Each entry is an upper bound. Lowering is good; raising means a regression.
BASELINE: dict[str, int] = {
    "src/exphub/agent/constants.py": 2,
    "src/exphub/agent/handlers.py": 2,
    "src/exphub/agent/rag.py": 2,
    "src/exphub/app/main.py": 1,
    "src/exphub/app/models/angle_plan.py": 0,
    "src/exphub/app/models/data_analysis.py": 7,
    "src/exphub/app/models/eic_client.py": 3,
    "src/exphub/app/models/eic_control.py": 0,
    "src/exphub/app/models/experiment_info.py": 0,
    "src/exphub/app/models/gonio_pvs.py": 0,
    "src/exphub/app/models/temporal_analysis.py": 0,
    "src/exphub/app/view_models/angle_plan.py": 6,
    "src/exphub/app/view_models/main.py": 6,
    "src/exphub/app/views/css_status.py": 115,
    "src/exphub/app/views/data_analysis.py": 1,
    "src/exphub/app/views/main_view.py": 0,
    "src/exphub/app/views/temporal_analysis.py": 2,
}

# Directories where hardcoded TOPAZ/BL12 references are LEGITIMATE
# (e.g. the topaz beamline plug-in itself, or test fixtures).
ALLOWED_PREFIXES = (
    "src/exphub/beamlines/",
    "tests/",
)

# Individual files that legitimately mention beamline ids (docstring examples
# inside framework code, etc.). One-off exceptions; prefer ALLOWED_PREFIXES.
ALLOWED_FILES = {
    "src/exphub/core/beamline/spec.py",
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


def test_no_unrecorded_coupling_sites() -> None:
    """Fail if a new file picks up TOPAZ/BL12 hardcoding outside allowed dirs."""
    counts = _scan()
    new_files = sorted(set(counts) - set(BASELINE))
    assert not new_files, (
        f"New file(s) with TOPAZ/BL12 hardcoding: {new_files}. "
        "Either de-hardcode (use BeamlineContext) or add an entry to BASELINE."
    )


def test_coupling_does_not_regress() -> None:
    """Fail if any file's TOPAZ/BL12 count exceeds the recorded baseline."""
    counts = _scan()
    regressions = {
        f: (counts[f], BASELINE[f])
        for f in BASELINE
        if counts.get(f, 0) > BASELINE[f]
    }
    assert not regressions, (
        f"Coupling regressed in: {regressions} "
        "(actual, allowed). De-hardcode or update BASELINE if intentional."
    )


def test_total_coupling_count() -> None:
    """Document total coupling so progress is visible in test output."""
    counts = _scan()
    total = sum(counts.values())
    # Total decreases as phases land. See MULTI_BEAMLINE_PLAN.md.
    assert total <= sum(BASELINE.values()), (
        f"Total hardcoded TOPAZ/BL12 references = {total}, "
        f"baseline = {sum(BASELINE.values())}."
    )

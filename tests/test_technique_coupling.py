"""Technique-coupling regression ratchet.

The multi-technique refactor (see ``MULTI_TECHNIQUE_PLAN.md``) is moving
single-crystal-shaped code (models, view-models, views) out of
``src/exphub/app/`` and ``src/exphub/core/`` into a per-technique package
``src/exphub/techniques/single_crystal/``. While the move is in flight,
this test acts as a *ratchet*: per-file baselines are recorded below and
each commit must keep counts at-or-below those baselines.

Baselines drop as each file move lands. The single-crystal root model moved to
``techniques/single_crystal/models/root.py`` (``SingleCrystalMainModel``) so it
no longer lives in ``app/``; the only residual left is the ``TabOverrides`` slot
field names in ``core/beamline/spec.py``, reshaped to technique-neutral names
next (#1b), which zeroes the ratchet (empty ``BASELINE`` map plus the strict
assertion).

Patterns matched (single-crystal vocabulary that should not live in
framework-agnostic code once the refactor finishes):
  - crystallography: crystalsystem, point_group, centering, UBFile, HKL, MNP
  - peak finding:    peak_radius, max_q, min_dspacing, max_dspacing,
                     IntegrateEllipsoids, FindUBUsingFFT, PredictPeaks
  - SC steering:     angle_plan, angleplan, temporal_analysis,
                     temporalanalysis, gonio_pvs
"""

from __future__ import annotations

import re
from pathlib import Path

# Word-boundary aware so we don't match "publisher" for "UB" or
# "ubuntu" for "UB" etc. ``\b`` works on word chars; for tokens that
# already include underscores the boundary is between word and non-word.
PATTERN = re.compile(
    r"\b("
    r"crystalsystem|"
    r"point_group|"
    r"centering|"
    r"UBFile|UBFileName|"
    r"HKL|MNP|"
    r"peak_radius|"
    r"max_q|min_dspacing|max_dspacing|"
    r"angle_plan|angleplan|"
    r"temporal_analysis|temporalanalysis|"
    r"gonio_pvs|"
    r"IntegrateEllipsoids|FindUBUsingFFT|FindPeaksMD|PredictPeaks|"
    r"SaveIsawPeaks|SaveIsawUB"
    r")\b"
)

# Scan only framework-agnostic dirs. ``techniques/`` (when it exists),
# ``beamlines/``, ``agent/``, and ``tests/`` are explicitly allowed to
# carry single-crystal vocabulary.
SCAN_PREFIXES = (
    "src/exphub/app/",
    "src/exphub/core/",
)

# Files exempted from the ratchet for the duration of the move.
# Empty today — additions are intentional and need plan-doc justification.
ALLOWED_FILES: set[str] = set()

REPO_ROOT = Path(__file__).resolve().parent.parent

# The single-crystal composite root model moved out of app/ to
# techniques/single_crystal/models/root.py (``SingleCrystalMainModel``, supplied
# via each manifest's ``root_model_factory``), so ``main_model.py`` is gone from
# the scanned dirs. One deferred file remains:
#   - core/beamline/spec.py (2): the TabOverrides slot field names
#     ``angle_plan`` / ``temporal_analysis`` are single-crystal-shaped; the
#     shared 5-slot TabOverrides model is reshaped next (#1b), zeroing the
#     ratchet.
# Each commit must keep counts at-or-below these numbers; files not listed must
# stay at zero.
BASELINE: dict[str, int] = {
    "src/exphub/core/beamline/spec.py": 2,
}


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
        if not any(rel.startswith(p) for p in SCAN_PREFIXES):
            continue
        if rel in ALLOWED_FILES:
            continue
        n = _count_matches(py)
        if n:
            counts[rel] = n
    return counts


def test_no_unrecorded_technique_coupling() -> None:
    """Fail if a previously-zero file picks up a single-crystal reference."""
    counts = _scan()
    new_files = sorted(f for f in counts if f not in BASELINE)
    assert not new_files, (
        "Single-crystal coupling found in files outside BASELINE:\n"
        + "\n".join(f"  {counts[f]:5d}  {f}" for f in new_files)
        + "\n\nEither move the code under techniques/single_crystal/ "
          "(preferred) or add the file path to BASELINE with the current "
          "count (only if migration is in progress and the plan calls for it)."
    )


def test_technique_coupling_does_not_regress() -> None:
    """Fail if any baselined file's count grows above its baseline."""
    counts = _scan()
    regressions: list[tuple[str, int, int]] = []
    for path, baseline in BASELINE.items():
        actual = counts.get(path, 0)
        if actual > baseline:
            regressions.append((path, baseline, actual))
    assert not regressions, (
        "Single-crystal coupling regressed in:\n"
        + "\n".join(
            f"  {path}  baseline={b}  now={a}" for path, b, a in regressions
        )
        + "\n\nEither bring the count back down or update BASELINE if the "
          "increase is intentional. The end state of P2 is BASELINE == {}."
    )


def test_total_coupling_within_cap() -> None:
    """Track total framework-side single-crystal coupling."""
    counts = _scan()
    total = sum(counts.values())
    # Cap tightened to the post-#1a residual (only the TabOverrides slot names in
    # spec.py remain). Reaches 0 in #1b.
    INITIAL_CAP = 2
    assert total <= INITIAL_CAP, (
        f"Total framework-side single-crystal coupling = {total}, "
        f"exceeds cap {INITIAL_CAP}. Move the offending code under "
        "techniques/<id>/ — app/ and core/ must stay technique-neutral."
    )

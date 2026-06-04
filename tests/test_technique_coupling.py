"""Technique-coupling regression ratchet.

The multi-technique refactor (see ``MULTI_TECHNIQUE_PLAN.md``) is moving
single-crystal-shaped code (models, view-models, views) out of
``src/exphub/app/`` and ``src/exphub/core/`` into a per-technique package
``src/exphub/techniques/single_crystal/``. While the move is in flight,
this test acts as a *ratchet*: per-file baselines are recorded below and
each commit must keep counts at-or-below those baselines.

Baselines dropped as each file move landed. The refactor is now complete: the
single-crystal root model moved to ``techniques/single_crystal/models/root.py``
(``SingleCrystalMainModel``) so it no longer lives in ``app/``, and the shared
``TabOverrides`` slots were renamed to technique-neutral, ``TabKey``-aligned
names (``ipts``/``live``/``steering``/``status``/``analysis``) so ``spec.py``
carries no single-crystal vocabulary. The residual is cleared: ``BASELINE`` is
now empty and ``INITIAL_CAP`` is 0 — the ratchet-zero gate is met. ``_scan()``
must return ``{}`` and any new single-crystal coupling in ``app/`` + ``core/``
fails the suite.

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

# The refactor is complete: every single-crystal-shaped module now lives under
# techniques/single_crystal/, all re-export shims are deleted, the tab dispatcher
# is manifest-driven, and the EIC client + control model live in core/eic/. The
# final two deferred files are now clean too:
#   - the single-crystal composite root model moved out of app/ to
#     techniques/single_crystal/models/root.py (``SingleCrystalMainModel``,
#     supplied via each manifest's ``root_model_factory``).
#   - core/beamline/spec.py ``TabOverrides`` slots were renamed to
#     technique-neutral, ``TabKey``-aligned names
#     (``ipts``/``live``/``steering``/``status``/``analysis``).
# BASELINE is now empty: every file under the scanned prefixes must stay at zero.
BASELINE: dict[str, int] = {}


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
        + "\n".join(f"  {path}  baseline={b}  now={a}" for path, b, a in regressions)
        + "\n\nEither bring the count back down or update BASELINE if the "
        "increase is intentional. The end state of P2 is BASELINE == {}."
    )


def test_total_coupling_within_cap() -> None:
    """Track total framework-side single-crystal coupling."""
    counts = _scan()
    total = sum(counts.values())
    # Ratchet-zero gate met: the refactor is complete and no single-crystal
    # vocabulary should remain in app/ + core/.
    initial_cap = 0
    assert total <= initial_cap, (
        f"Total framework-side single-crystal coupling = {total}, "
        f"exceeds cap {initial_cap}. Move the offending code under "
        "techniques/<id>/ — app/ and core/ must stay technique-neutral."
    )

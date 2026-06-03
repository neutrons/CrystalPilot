"""End-state acceptance checks for the multi-technique refactor.

Codifies the machine-checkable items of the "End-state acceptance check"
section of ``MULTI_TECHNIQUE_PLAN.md``:

  1. A grep of single-crystal identifiers over ``src/exphub/app`` and
     ``src/exphub/core`` returns the documented residual.
  2. The repo ships ``techniques/single_crystal`` + ``techniques/sans`` and
     they register their manifests.
  3. The repo ships ``beamlines/topaz``, ``beamlines/corelli`` and
     ``beamlines/usans`` and they register their specs.

The remaining acceptance items (mypy --strict cleanliness, the grayed-out
cross-technique selector banner, the agent reading the active manifest, and
``MainApp()`` constructing under ``set_active("usans")``) are exercised by
their own dedicated tests/suites; this file pins the structural end-state and
the coupling residual so a regression in either is caught immediately.

Plan item 1 now returns *zero* single-crystal references: the refactor is
complete. The single-crystal root model moved to
``techniques/single_crystal/models/root.py`` (``SingleCrystalMainModel``) and the
shared ``TabOverrides`` slots were renamed to technique-neutral, ``TabKey``-aligned
names, clearing the last deferred residual. This test asserts the residual set is
empty (== fully clean) and tracks the ratchet ``BASELINE`` so the two cannot
disagree.
"""

from __future__ import annotations

from pathlib import Path

from test_technique_coupling import BASELINE, _scan

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "exphub"

# The single-crystal coupling residual in the framework-agnostic dirs (``app/``
# + ``core/``). Now empty: plan item 1 is fully satisfied (grep == 0 results).
# Mirrors the ratchet BASELINE.
EXPECTED_RESIDUAL: dict[str, int] = {}


def test_single_crystal_coupling_matches_documented_residual() -> None:
    """Acceptance item 1: the app/core single-crystal grep == documented residual.

    Uses the same scanner + pattern as the technique-coupling ratchet so the two
    tests can never disagree. The end state is ``EXPECTED_RESIDUAL == {}`` (grep
    returns 0); until the deferred phases land it must match the recorded set
    exactly — neither growing (new coupling) nor unexpectedly shrinking without
    this constant being updated alongside the ratchet BASELINE.
    """
    counts = _scan()
    assert counts == EXPECTED_RESIDUAL, (
        "app/+core single-crystal coupling drifted from the documented "
        f"residual.\n  expected: {EXPECTED_RESIDUAL}\n  actual:   {counts}\n\n"
        "If a deferred phase removed coupling, drop the now-zero file from "
        "EXPECTED_RESIDUAL here and from BASELINE in test_technique_coupling.py "
        "(and lower its INITIAL_CAP). If new coupling appeared, move it under "
        "techniques/<id>/ instead."
    )


def test_acceptance_residual_tracks_ratchet_baseline() -> None:
    """The acceptance residual and the ratchet BASELINE must stay in lockstep."""
    assert EXPECTED_RESIDUAL == BASELINE, (
        "EXPECTED_RESIDUAL here and BASELINE in test_technique_coupling.py have "
        "diverged; keep them identical so the two tests agree."
    )


def test_ships_single_crystal_and_sans_techniques() -> None:
    """Acceptance item 2: techniques/single_crystal + techniques/sans ship."""
    for tech_id in ("single_crystal", "sans"):
        pkg = SRC / "techniques" / tech_id
        assert (pkg / "__init__.py").is_file(), f"missing techniques/{tech_id}/"
        assert (pkg / "manifest.py").is_file(), (
            f"missing techniques/{tech_id}/manifest.py"
        )


def test_techniques_register_their_manifests() -> None:
    """Acceptance item 2 (wired): both technique manifests register and self-id.

    ``get_technique`` lazily imports ``exphub.techniques.<id>`` on first access,
    so this exercises the real discovery path without touching registry state.
    """
    from exphub.core.beamline import technique as technique_mod

    for tech_id in ("single_crystal", "sans"):
        manifest = technique_mod.get_technique(tech_id)
        assert manifest.id == tech_id
        # A real technique contributes at least its default tab set.
        assert manifest.default_tabs, f"{tech_id} manifest declares no tabs"


def test_ships_topaz_corelli_usans_beamlines() -> None:
    """Acceptance item 3: beamlines/topaz + corelli + usans ship."""
    for bl_id in ("topaz", "corelli", "usans"):
        pkg = SRC / "beamlines" / bl_id
        assert (pkg / "__init__.py").is_file(), f"missing beamlines/{bl_id}/"
        assert (pkg / "spec.py").is_file(), f"missing beamlines/{bl_id}/spec.py"


def test_beamlines_register_and_bind_to_techniques() -> None:
    """Acceptance item 3 (wired): all three beamlines register on their technique.

    topaz + corelli are single-crystal; usans is the first sans beamline.
    ``list_ids``/``get`` lazily import ``exphub.beamlines`` (triggering each
    spec's registration side effect), so this needs no registry-state setup.
    """
    from exphub.core.beamline import registry

    ids = set(registry.list_ids())
    assert {"topaz", "corelli", "usans"} <= ids, (
        f"expected topaz/corelli/usans registered; got {sorted(ids)}"
    )
    assert registry.get("topaz").technique == "single_crystal"
    assert registry.get("corelli").technique == "single_crystal"
    assert registry.get("usans").technique == "sans"

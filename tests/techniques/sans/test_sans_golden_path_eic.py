"""Golden-path integration test (SANS): flexible strategy table -> submit to EIC.

The SANS technique reuses the framework's :class:`EICControlModel`; only the row
builder differs. This drives the real submit chain — the SANS row builder
(resolved off the manifest) -> ``submit_jobs`` -> the EIC client — against the
recording fake EIC, with no network, proving:

  - the SANS submit path works and USANS resolves to its EIC beamline code
    (the ``_default_beamline_database`` regression fix), and
  - rows are **grouped by BL1A:sampleholder** into one table-scan per Sample
    (the flexible-column / per-Sample-submission behaviour).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import exphub.beamlines  # noqa: F401 — registers TOPAZ + CORELLI + USANS
from exphub.core.beamline import active_technique, set_active
from exphub.core.eic.control import EICControlModel
from exphub.techniques.sans.models.strategy import SansStrategyModel

_FIXTURE = Path(__file__).parent / "fixtures" / "strategy.csv"


def teardown_module(_module: object) -> None:
    set_active("topaz")  # leave the process on a single-crystal beamline


def _loaded_strategy() -> SansStrategyModel:
    model = SansStrategyModel()
    model.load_strategy(str(_FIXTURE))
    return model


def test_sans_build_jobs_groups_by_sample_holder() -> None:
    model = _loaded_strategy()
    builder = active_technique_sans().eic_row_builder
    jobs = builder.build_jobs(model.strategy_list)

    # 3 distinct holders (1, 2, 3) -> 3 jobs, holder-sorted.
    assert [j["title"] for j in jobs] == ["Sample 1", "Sample 2", "Sample 3"]
    # Holder 2 carries all 5 of its steps in one multi-row job.
    assert [len(j["rows"]) for j in jobs] == [1, 5, 1]
    # Headers are the flexible CSV columns, verbatim (incl. the colon in the PV name).
    assert jobs[0]["headers"] == ["Notes", "BL1A:sampleholder", "BL1A:anlge", "Wait For", "Value"]
    # SANS has no goniometer, so jobs carry no phi/omega metadata.
    assert all("phi" not in job and "omega" not in job for job in jobs)


def active_technique_sans() -> Any:
    set_active("usans")
    manifest = active_technique()
    assert manifest.id == "sans"
    builder = manifest.eic_row_builder
    assert builder is not None, "SANS manifest must expose an eic_row_builder"
    return manifest


def test_sans_submit_strategy_reaches_eic(fake_eic: Any) -> None:
    set_active("usans")
    builder = active_technique().eic_row_builder
    assert builder is not None

    model = _loaded_strategy()
    jobs = builder.build_jobs(model.strategy_list)
    assert len(jobs) == 3

    ctrl = EICControlModel()
    ctrl.is_simulation = True
    ctrl.submit_jobs(jobs, ipts_number="IPTS-77", instrument_name="USANS")

    # USANS resolved to its EIC beamline code (regression-fix guard).
    assert ctrl.supported_beamline is True
    assert ctrl.beamline == "bl1a"

    submitted = fake_eic.all_submitted
    # One table-scan per Sample; each scan carries that Sample's full row set.
    assert [len(s["parms"]["rows"]) for s in submitted] == [1, 5, 1]
    assert ctrl.eic_submission_success == [True, True, True]
    assert [j["title"] for j in ctrl.submitted_jobs] == ["Sample 1", "Sample 2", "Sample 3"]
    # No goniometer angles -> phi/omega default to 0.0 in the submitted-job rows.
    assert all(j["phi"] == 0.0 and j["omega"] == 0.0 for j in ctrl.submitted_jobs)


def test_single_crystal_submit_still_uses_singular_row(fake_eic: Any) -> None:
    """The additive ``rows`` payload must not change single-crystal submission."""
    set_active("topaz")
    builder = active_technique().eic_row_builder
    assert builder is not None
    sc_row = {"title": "sc1", "comment": "", "omega": 10.0, "phi": 5.0, "wait_for": "PCharge", "value": 1.0}
    jobs = builder.build_jobs([sc_row])
    # Single-crystal jobs carry a singular ``row`` (no ``rows``).
    assert "row" in jobs[0] and "rows" not in jobs[0]

    ctrl = EICControlModel()
    ctrl.is_simulation = True
    ctrl.submit_jobs(jobs, ipts_number="IPTS-1", instrument_name="TOPAZ")
    # submit_jobs wrapped the singular row into a one-row table scan.
    assert [len(s["parms"]["rows"]) for s in fake_eic.all_submitted] == [1]

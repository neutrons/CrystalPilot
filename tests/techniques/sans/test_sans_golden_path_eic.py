"""Golden-path integration test (SANS): strategy table -> submit to EIC.

The SANS technique reuses the framework's :class:`EICControlModel`; only the
row builder differs. This drives the real submit chain — the SANS row builder
(resolved off the manifest) -> ``submit_jobs`` -> the EIC client — against the
recording fake EIC, with no network, proving the SANS submit path works and
that USANS resolves to its EIC beamline code (the ``_default_beamline_database``
regression fix). SANS strategy column values are still provisional (HANDOFF),
so this pins the *plumbing*, not the exact column semantics.
"""

from __future__ import annotations

from typing import Any

import exphub.beamlines  # noqa: F401 — registers TOPAZ + CORELLI + USANS
from exphub.core.beamline import active_technique, set_active
from exphub.core.eic.control import EICControlModel
from exphub.techniques.sans.models.strategy import SansStrategyModel


def teardown_module(_module: object) -> None:
    set_active("topaz")  # leave the process on a single-crystal beamline


def _two_strategy_rows() -> list[dict]:
    """Two SANS strategy rows built from the model's own default record."""
    model = SansStrategyModel()
    a = dict(model.get_default_run_record())
    a.update({"title": "sans1", "sample_aperture": 10.0, "detector_distance": 4.0})
    b = dict(model.get_default_run_record())
    b.update({"title": "sans2", "sample_aperture": 20.0, "detector_distance": 8.0})
    return [a, b]


def test_sans_submit_strategy_reaches_eic(fake_eic: Any) -> None:
    set_active("usans")
    builder = active_technique().eic_row_builder
    assert builder is not None, "SANS manifest must expose an eic_row_builder"

    strategy = _two_strategy_rows()
    jobs = builder.build_jobs(strategy)
    assert len(jobs) == 2
    # SANS has no goniometer, so jobs carry no phi/omega metadata.
    assert all("phi" not in job and "omega" not in job for job in jobs)

    ctrl = EICControlModel()
    ctrl.is_simulation = True
    ctrl.submit_jobs(jobs, ipts_number="IPTS-77", instrument_name="USANS")

    # USANS resolved to its EIC beamline code (regression-fix guard).
    assert ctrl.supported_beamline is True
    assert ctrl.beamline == "bl1a"

    submitted = fake_eic.all_submitted
    assert [s["parms"]["rows"][0] for s in submitted] == [job["row"] for job in jobs]
    assert ctrl.eic_submission_success == [True, True]
    assert [j["title"] for j in ctrl.submitted_jobs] == ["sans1", "sans2"]
    # No goniometer angles -> phi/omega default to 0.0 in the submitted-job rows.
    assert all(j["phi"] == 0.0 and j["omega"] == 0.0 for j in ctrl.submitted_jobs)

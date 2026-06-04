"""Golden-path test (single crystal): temporal analysis with a fake Mantid workflow.

The real ``MantidWorkflow`` needs a Mantid live-data stream, so the live-reduction
*consumption* logic (series selection for the figures, UB sync) had no test at
all. The ``fake_mantid_workflow`` fixture (tests/conftest.py) patches the
workflow class so ``start_reading_live_mtd_data`` builds a recorded fake; this
test then drives the model's series helpers — the same code paths whose
``assert wf is not None`` guards were added in the mypy pass.
"""

from __future__ import annotations

from typing import Any

import exphub.beamlines  # noqa: F401 — registers beamlines
from exphub.core.beamline import set_active
from exphub.techniques.single_crystal.models.root import SingleCrystalMainModel


def teardown_module(_module: object) -> None:
    set_active("topaz")


def _temporal_model() -> Any:
    set_active("topaz")
    return SingleCrystalMainModel().temporalanalysis


def test_start_reading_uses_injected_fake(fake_mantid_workflow: Any) -> None:
    ta = _temporal_model()
    ta.start_reading_live_mtd_data()
    # The fixture returns the fake class it patched in.
    assert isinstance(ta.mtd_workflow, fake_mantid_workflow)
    # The live-data collection was "started" on the fake (no real Mantid stream).
    assert ta.mtd_workflow.live_starts == 1


def test_poisson_series_read_from_workflow(fake_mantid_workflow: Any) -> None:
    ta = _temporal_model()
    ta.start_reading_live_mtd_data()
    wf = ta.mtd_workflow
    assert wf is not None

    ta.prediction_model_type = "Poisson Model"
    times, intensity = ta._series_for_intensity()
    assert times == wf.measure_times
    assert intensity == wf.intensity_ratios

    unc_times, unc = ta._series_for_uncertainty()
    assert unc_times == wf.measure_times
    assert unc == wf.rsigs


def test_alternate_model_series_read_from_workflow(fake_mantid_workflow: Any) -> None:
    ta = _temporal_model()
    ta.start_reading_live_mtd_data()
    wf = ta.mtd_workflow
    assert wf is not None

    # Any non-"Poisson Model" option takes the timeseries branch.
    ta.prediction_model_type = "Bayesian Model"
    times, _intensity = ta._series_for_intensity()
    assert times == wf.timeseries_plt

    unc_times, unc = ta._series_for_uncertainty()
    assert unc_times == wf.timeseries_plt
    assert unc == wf.temporal_poisson_uncertainty


def test_restart_stops_previous_workflow(fake_mantid_workflow: Any) -> None:
    ta = _temporal_model()
    ta.start_reading_live_mtd_data()
    first = ta.mtd_workflow
    assert first is not None

    ta.start_reading_live_mtd_data()  # restart: must stop the previous instance
    assert first.stopped is True
    assert ta.mtd_workflow is not first

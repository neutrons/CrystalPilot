"""Golden-path integration test (single crystal): angle plan -> submit to EIC.

Exercises the real submission chain end to end — the single-crystal row builder
-> :meth:`EICControlModel.submit_jobs` -> the EIC client — against a recording
fake EIC (``fake_eic`` fixture in ``tests/conftest.py``), with no network. This
is the behavioral safety net the structural suite lacked (HANDOFF item B), and
it covers ``submit`` / ``poll`` / ``abort`` — the destructive paths.

It also pins the regression fix for ``_default_beamline_database``: before the
fix that helper collapsed to ``{}`` whenever a non-single-crystal beamline was
registered, which silently made *every* technique's submit bail with
``supported_beamline = False``.
"""

from __future__ import annotations

import importlib
from typing import Any

import exphub.beamlines  # noqa: F401 — registers TOPAZ + CORELLI + USANS
from exphub.core.beamline import set_active
from exphub.core.eic.control import EICControlModel

# Two angle rows (PCharge wait + a non-PCharge wait) and one temperature ramp —
# the same plan shape the row-builder golden test uses.
_PLAN = [
    {"title": "run1", "comment": "c1", "omega": 10.0, "phi": 20.0, "wait_for": "PCharge", "value": 30},
    {"title": "run2", "comment": "c2", "omega": 5.5, "phi": -3.2, "wait_for": "Time", "value": 60},
    {
        "title": "ramp1",
        "comment": "rc",
        "step_type": "ramp",
        "ramp_start": 100,
        "ramp_end": 300,
        "ramp_rate": 2,
        "ramp_soak": 5,
        "ramp_run": 1,
    },
]


def _builder_for(beamline_id: str) -> tuple[Any, str]:
    """Activate ``beamline_id`` and return its (reloaded) builder + AMBIENT const.

    Mirrors a restart-switch: the ``gonio_pvs`` shim caches the active beamline's
    PV strings at import, so it (and the builder that reads it) must be reloaded
    after ``set_active`` — exactly what ``test_eic_row_builder`` does.
    """
    set_active(beamline_id)
    gonio = importlib.import_module("exphub.techniques.single_crystal.models.gonio_pvs")
    importlib.reload(gonio)
    rb = importlib.import_module("exphub.techniques.single_crystal.agent.eic_row_builder")
    importlib.reload(rb)
    return rb.SINGLE_CRYSTAL_EIC_ROW_BUILDER, gonio.AMBIENT


def teardown_module(_module: object) -> None:
    # Restore TOPAZ + a TOPAZ-consistent shim for the rest of the suite.
    _builder_for("topaz")


def test_submit_angle_plan_reaches_eic(fake_eic: Any) -> None:
    """build_jobs -> submit_jobs -> EIC client, with the right rows + state."""
    builder, ambient = _builder_for("topaz")
    jobs = builder.build_jobs(_PLAN, goniometer_type=ambient)

    ctrl = EICControlModel()
    ctrl.is_simulation = True
    ctrl.submit_jobs(jobs, ipts_number="IPTS-1234", instrument_name="TOPAZ")

    # The instrument resolved to its EIC beamline code (regression-fix guard).
    assert ctrl.supported_beamline is True
    assert ctrl.beamline == "bl12"

    # Exactly one client was built and enablement was checked once.
    assert len(fake_eic.instances) == 1
    assert fake_eic.last.enabled_checks == 1

    # Every job's row reached EIC, in order, as a single-row table scan.
    submitted = fake_eic.all_submitted
    assert [s["parms"]["rows"][0] for s in submitted] == [job["row"] for job in jobs]
    assert [s["parms"]["headers"] for s in submitted] == [job["headers"] for job in jobs]
    assert all(s["simulate_only"] is True for s in submitted)

    # Control-model state reflects the submission.
    assert ctrl.eic_submission_success == [True, True, True]
    assert len(ctrl.submitted_jobs) == 3
    assert [j["scan_id"] for j in ctrl.submitted_jobs] == [1000, 1001, 1002]
    assert all(j["status"] == "submitted" for j in ctrl.submitted_jobs)
    assert ctrl.eic_submission_scan_id == 1000


def test_submit_respects_real_submission_flag(fake_eic: Any) -> None:
    """is_simulation=False must propagate to the EIC client (a real submit)."""
    builder, ambient = _builder_for("topaz")
    jobs = builder.build_jobs(_PLAN, goniometer_type=ambient)

    ctrl = EICControlModel()
    ctrl.is_simulation = False
    ctrl.submit_jobs(jobs, ipts_number="IPTS-1234", instrument_name="TOPAZ")

    assert fake_eic.all_submitted, "nothing was submitted"
    assert all(s["simulate_only"] is False for s in fake_eic.all_submitted)


def test_unregistered_instrument_does_not_submit(fake_eic: Any) -> None:
    """An instrument with no beamline code must bail without contacting EIC."""
    builder, ambient = _builder_for("topaz")
    jobs = builder.build_jobs(_PLAN, goniometer_type=ambient)

    ctrl = EICControlModel()
    ctrl.submit_jobs(jobs, ipts_number="IPTS-1234", instrument_name="NOT_A_BEAMLINE")

    assert ctrl.supported_beamline is False
    assert fake_eic.instances == []  # no client constructed, no network attempted
    assert ctrl.submitted_jobs == []


def test_poll_then_abort(fake_eic: Any) -> None:
    """After submit, polling marks jobs done and abort cancels via the client."""
    builder, ambient = _builder_for("topaz")
    jobs = builder.build_jobs(_PLAN, goniometer_type=ambient)

    ctrl = EICControlModel()
    ctrl.submit_jobs(jobs, ipts_number="IPTS-1234", instrument_name="TOPAZ")

    ctrl.poll_job_statuses("IPTS-1234", "TOPAZ")
    assert all(j["status"] == "done" and j["is_done"] for j in ctrl.submitted_jobs)

    scan_id = ctrl.submitted_jobs[0]["scan_id"]
    ctrl.abort_job(scan_id, "IPTS-1234", "TOPAZ")
    assert any(scan_id in inst.aborted for inst in fake_eic.instances)
    assert ctrl.submitted_jobs[0]["status"] == "aborted"
    assert ctrl.submitted_jobs[0]["is_done"] is True

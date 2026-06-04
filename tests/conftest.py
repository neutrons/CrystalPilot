"""Shared pytest fixtures: behavioral fakes for the hard external dependencies.

The structural suite proves things *construct* and that ratchets hold; these
fakes let golden-path integration tests exercise the real science workflow
(load IPTS -> build strategy -> submit -> observe) without a live EIC server,
a Mantid live-data stream, or EPICS hardware. See HANDOFF.md item B.

Both fakes drop in at a monkeypatchable seam:
  - ``exphub.core.eic.control.EICClient`` (the EIC submission client), and
  - ``...temporal_analysis.model.MantidWorkflow`` (the Mantid live workflow).

EPICS needs no fake: PVs are plain string constants passed to EIC as column
names; real channel access lives only in the (untested) trame view layer.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest
from langchain_core.messages import AIMessage


class FakeEICClient:
    """In-memory stand-in for :class:`exphub.core.eic.eic_client.EICClient`.

    Implements only the surface :class:`EICControlModel` drives
    (``is_eic_enabled`` / ``submit_table_scan`` / ``get_scan_status`` /
    ``abort_scan``) and records every call so a test can assert exactly what
    would have hit the real EIC service. Performs no network I/O.
    """

    def __init__(self, token: Any = None, beamline: Any = None, ipts_number: Any = None, **_: Any) -> None:
        self.token = token
        self.beamline = beamline
        self.ipts_number = ipts_number
        self.submitted: list[dict[str, Any]] = []
        self.aborted: list[int] = []
        self.status_checks: list[int] = []
        self.enabled_checks = 0
        self._next_scan_id = 1000

    def is_eic_enabled(self, print_results: bool = False, **_: Any) -> bool:
        self.enabled_checks += 1
        return True

    def submit_table_scan(
        self, parms: dict | None = None, desc: str = "", simulate_only: bool = True, **_: Any
    ) -> tuple[bool, int, dict[str, str]]:
        self.submitted.append({"parms": parms, "desc": desc, "simulate_only": simulate_only})
        scan_id = self._next_scan_id
        self._next_scan_id += 1
        return True, scan_id, {"eic_response_message": "submitted (fake)"}

    def get_scan_status(self, scan_id: int | None = None, **_: Any) -> tuple[bool, bool, str, dict[str, str]]:
        self.status_checks.append(scan_id if scan_id is not None else -1)
        return True, True, "done", {"eic_response_message": "done (fake)"}

    def abort_scan(self, scan_id: int | None = None, **_: Any) -> tuple[bool, dict[str, str]]:
        self.aborted.append(scan_id if scan_id is not None else -1)
        return True, {"eic_response_message": "aborted (fake)"}


class FakeEICClientFactory:
    """Callable matching the ``EICClient`` constructor that records instances.

    ``EICControlModel`` builds a fresh client inside each method, so patching the
    class with this factory lets a test see every client that was created and
    every call it received.
    """

    def __init__(self) -> None:
        self.instances: list[FakeEICClient] = []

    def __call__(
        self, token: Any = None, beamline: Any = None, ipts_number: Any = None, **kwargs: Any
    ) -> FakeEICClient:
        inst = FakeEICClient(token, beamline, ipts_number, **kwargs)
        self.instances.append(inst)
        return inst

    @property
    def last(self) -> FakeEICClient:
        assert self.instances, "no FakeEICClient was constructed"
        return self.instances[-1]

    @property
    def all_submitted(self) -> list[dict[str, Any]]:
        return [s for inst in self.instances for s in inst.submitted]


@pytest.fixture
def fake_eic(monkeypatch: pytest.MonkeyPatch) -> FakeEICClientFactory:
    """Patch ``EICControlModel``'s ``EICClient`` with a recording fake (no network)."""
    factory = FakeEICClientFactory()
    monkeypatch.setattr("exphub.core.eic.control.EICClient", factory)
    return factory


class FakeMantidWorkflow:
    """Recorded stand-in for ``MantidWorkflow`` — no Mantid live stream/algorithms.

    Pre-populated with deterministic series so the temporal-analysis model's
    series/figure dispatch and uncertainty-based auto-stop logic can be exercised
    headless. Methods that would otherwise drive Mantid are no-ops (or record a
    call). The attribute surface mirrors what the model + steering VM read.
    """

    def __init__(self) -> None:
        # Series consumed by TemporalAnalysisModel._series_for_intensity/_uncertainty
        self.measure_times: list[float] = [0.0, 1.0, 2.0]
        self.intensity_ratios: list[float] = [10.0, 10.5, 11.0]
        self.rsigs: list[float] = [5.0, 3.0, 1.0]
        self.timeseries_plt: list[float] = [0.0, 1.0, 2.0]
        self.timeseries_data_plt: list[float] = [10.0, 10.5, 11.0]
        self.temporal_poisson_intensity: list[float] = [100.0, 105.0, 110.0]
        # Last value is below the default 0.1 auto-stop threshold (control model).
        self.temporal_poisson_uncertainty: list[float] = [0.30, 0.12, 0.05]
        self.latest_ub: list[list[float]] | None = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        self.latest_lattice: dict[str, float] | None = {
            "a": 5.0,
            "b": 5.0,
            "c": 5.0,
            "alpha": 90.0,
            "beta": 90.0,
            "gamma": 90.0,
            "volume": 125.0,
        }
        # Call counters for assertions.
        self.update_calls = 0
        self.reductions = 0
        self.live_starts = 0
        self.stopped = False

    def update_experiment_info(self, _models: Any) -> None:
        self.update_calls += 1

    def start_live_data_collection_instances(self) -> None:
        self.live_starts += 1

    def live_data_reduction(self) -> None:
        self.reductions += 1

    def stop(self) -> None:
        self.stopped = True

    def get_latest_ub(self, workspace_name: str = "live_predict_peaks_ws") -> list[list[float]] | None:
        return self.latest_ub

    def get_latest_lattice(self, workspace_name: str = "live_predict_peaks_ws") -> dict[str, float] | None:
        return self.latest_lattice

    def save_latest_ub(self, workspace_name: str = "live_predict_peaks_ws") -> str | None:
        return None


@pytest.fixture
def fake_mantid_workflow(monkeypatch: pytest.MonkeyPatch) -> type[FakeMantidWorkflow]:
    """Patch ``MantidWorkflow`` so ``start_reading_live_mtd_data`` builds the fake."""
    monkeypatch.setattr(
        "exphub.techniques.single_crystal.models.temporal_analysis.model.MantidWorkflow",
        FakeMantidWorkflow,
    )
    return FakeMantidWorkflow


# --------------------------------------------------------------------------- agent eval harness


class ScriptedChatModel:
    """Deterministic stand-in for the configured chat model (agent eval harness).

    Replays pre-scripted ``AIMessage`` objects on successive ``invoke`` calls so
    the agent's graph (tool dispatch -> execution -> validation -> reply) can be
    evaluated without a real LLM or network. ``bind_tools`` is a no-op — the
    script, not the model, decides which tools are "called".
    """

    def __init__(self, responses: list[AIMessage]) -> None:
        self._responses = list(responses)
        self._i = 0
        self.invocations = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedChatModel":
        return self

    def invoke(self, messages: Any, **kwargs: Any) -> AIMessage:
        self.invocations += 1
        if self._i >= len(self._responses):
            return AIMessage(content="")  # script underflow -> end the turn
        resp = self._responses[self._i]
        self._i += 1
        return resp


@pytest.fixture
def scripted_agent_llm(monkeypatch: pytest.MonkeyPatch) -> Callable[[list[AIMessage]], ScriptedChatModel]:
    """Make ``Agent.invoke`` deterministic: scripted LLM + disabled RAG.

    Returns an installer: pass a list of ``AIMessage`` objects and it patches the
    agent's LLM seam so the SAME scripted model is replayed across every graph
    round in the turn. Build the messages with the test module's small
    ``ai_tool_call`` / ``ai_reply`` helpers.
    """

    class _NoRag:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("RAG disabled in the agent eval harness")

    monkeypatch.setattr("exphub.agent.agent.BeamlineKnowledgeBase", _NoRag)

    def _install(responses: list[AIMessage]) -> ScriptedChatModel:
        model = ScriptedChatModel(responses)
        monkeypatch.setattr("exphub.agent.agent.get_configured_chat_model", lambda: model)
        return model

    return _install

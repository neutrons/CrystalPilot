"""Shared constants for the agent.

Tab mappings remain here. Experiment presets used to be hardcoded per
instrument in this file; they now live on each beamline plug-in's
``AgentSpec.presets`` and are aggregated at call time by
:func:`get_experiment_presets`. Adding a new instrument's preset means
populating the new beamline's spec — no edit to agent code.
"""

from __future__ import annotations


def get_experiment_presets() -> dict[str, dict]:
    """Return every preset declared by every registered beamline.

    Keys collide intentionally if two beamlines declare the same name;
    later registrations win. In practice each beamline namespaces its
    presets (e.g. ``<id>_standard``) so collisions are not expected.
    """
    from ..core.beamline import get as _get
    from ..core.beamline import list_ids as _list_ids

    presets: dict[str, dict] = {}
    for bid in _list_ids():
        try:
            presets.update(_get(bid).agent.presets)
        except Exception:
            continue
    return presets


# ---------------------------------------------------------------------------
# Tab navigation mappings
# ---------------------------------------------------------------------------
TAB_MAP: dict[str, int] = {
    "ipts_info": 1, "ipts": 1,
    "live_data_processing": 2, "live_data": 2, "temporal_analysis": 2,
    "experiment_steering": 3, "angle_plan": 3,
    "instrument_status": 5, "css_status": 5,
    "data_analysis": 6,
}

TAB_NAMES: dict[int, str] = {
    1: "IPTS Info",
    2: "Live Data Processing",
    3: "Experiment Steering",
    5: "Instrument Status",
    6: "Data Analysis",
}

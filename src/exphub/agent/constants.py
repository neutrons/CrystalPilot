"""Shared constants for the CrystalPilot agent.

Centralises experiment presets, tab mappings, and other values that are
referenced by multiple modules.  Extend ``EXPERIMENT_PRESETS`` to add new
instrument presets without touching agent or tool code.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Experiment presets — named parameter bundles the agent can apply at once.
# ---------------------------------------------------------------------------
EXPERIMENT_PRESETS: dict[str, dict] = {
    "topaz_standard": {
        "instrument": "TOPAZ",
        "max_q": 17.0,
        "num_peaks_to_find": 500,
        "tolerance": 0.12,
        "predict_peaks": True,
        "peak_radius": 0.11,
        "bkg_inner_radius": 0.115,
        "bkg_outer_radius": 0.14,
        "pred_min_dspacing": 0.499,
        "pred_max_dspacing": 11.0,
        "pred_min_wavelength": 0.4,
        "pred_max_wavelength": 3.45,
    },
    "corelli_standard": {
        "instrument": "CORELLI",
        "max_q": 14.0,
        "num_peaks_to_find": 300,
        "tolerance": 0.15,
        "predict_peaks": True,
        "peak_radius": 0.13,
        "bkg_inner_radius": 0.135,
        "bkg_outer_radius": 0.16,
        "pred_min_dspacing": 0.5,
        "pred_max_dspacing": 10.0,
        "pred_min_wavelength": 0.7,
        "pred_max_wavelength": 2.89,
    },
    "mandi_standard": {
        "instrument": "MANDI",
        "max_q": 10.0,
        "num_peaks_to_find": 200,
        "tolerance": 0.10,
        "predict_peaks": True,
        "pred_min_dspacing": 0.7,
        "pred_max_dspacing": 7.0,
        "pred_min_wavelength": 0.8,
        "pred_max_wavelength": 4.0,
    },
}


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

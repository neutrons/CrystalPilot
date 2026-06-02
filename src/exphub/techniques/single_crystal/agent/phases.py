"""The single-crystal experiment phase sequence (for the agent PhaseManager).

Moved verbatim from the former module-level ``PHASES`` in
``exphub.agent.workflow`` (P1.b). The legacy integer tab numbers (1/2/3/5/6)
are now :class:`~exphub.core.beamline.technique.TabKey` values; the per-phase
``label`` preserves the original ``tab_name`` (which sometimes differs from the
tab's own label, e.g. the *submit* phase lives on the steering tab but is
labelled "EIC Control").
"""

from __future__ import annotations

from ....core.beamline import PhaseDefinition, TabKey

# The 7 single-crystal phases in order.
SINGLE_CRYSTAL_PHASES: tuple[PhaseDefinition, ...] = (
    PhaseDefinition(
        name="setup",
        tab=TabKey.IPTS,
        label="IPTS Info",
        description="Enter experiment metadata: IPTS, crystal system, sample info",
        field_prefixes=(
            "ipts_number", "exp_name", "instrument", "molecular_formula", "Z",
            "unit_cell_volume", "sample_radius", "crystalsystem", "centering",
            "point_group", "cal_filename", "data_directory", "base_dir",
            "read_ub", "UBFileName",
        ),
    ),
    PhaseDefinition(
        name="monitor",
        tab=TabKey.LIVE,
        label="Live Data Processing",
        description="Stream live reduction results and confirm data quality",
    ),
    PhaseDefinition(
        name="plan",
        tab=TabKey.STEERING,
        label="Experiment Steering",
        description="Generate an initial angle plan for reciprocal space coverage",
        field_prefixes=(
            "max_q", "num_peaks_to_find", "tolerance", "predict_peaks",
            "peak_radius", "bkg_inner_radius", "bkg_outer_radius",
            "pred_min_dspacing", "pred_max_dspacing",
            "pred_min_wavelength", "pred_max_wavelength",
            "abc_min", "abc_max", "edge_pixels", "split_threshold",
            "ellipse_size_specified", "subtract_bkg", "background_filename",
        ),
    ),
    PhaseDefinition(
        name="refine_plan",
        tab=TabKey.STEERING,
        label="Experiment Steering",
        description="Edit the angle plan — add, remove, or modify runs",
        field_prefixes=("angle_list_pd",),
    ),
    PhaseDefinition(
        name="submit",
        tab=TabKey.STEERING,
        label="EIC Control",
        description="Submit the angle plan to EIC for execution",
    ),
    PhaseDefinition(
        name="observe",
        tab=TabKey.STATUS,
        label="Instrument Status",
        description="Monitor motor positions and scan progress",
    ),
    PhaseDefinition(
        name="analyse",
        tab=TabKey.ANALYSIS,
        label="Data Analysis",
        description="Run data reduction and analysis on collected runs",
        field_prefixes=(
            "spectra_filename", "norm_to_wavelength", "scale_factor",
            "min_intensity", "min_isigi", "z_score", "border_pixels",
            "min_dspacing", "max_dspacing", "min_wavelength", "max_wavelength",
            "starting_batch_number", "SAFile", "FluxFile",
            "index_satellite_peaks", "mod_vec_1", "mod_vec_2", "mod_vec_3",
            "mod_vec_1_dh", "mod_vec_1_dk", "mod_vec_1_dl",
            "mod_vec_2_dh", "mod_vec_2_dk", "mod_vec_2_dl",
            "mod_vec_3_dh", "mod_vec_3_dk", "mod_vec_3_dl",
            "max_order", "cross_terms", "save_mod_info",
            "tolerance_satellite",
            "sat_peak_radius", "sat_peak_region_radius",
            "sat_peak_inner_radius", "sat_peak_outer_radius",
        ),
    ),
)

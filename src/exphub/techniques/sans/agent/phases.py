"""The SANS experiment phase sequence (for the agent PhaseManager).

The SANS analogue of
:data:`~exphub.techniques.single_crystal.agent.phases.SINGLE_CRYSTAL_PHASES`.
SANS has no reciprocal lattice to cover, so the phase machine has no UB /
angle-plan / peak-finding steps. The five SANS phases map onto the same five
:class:`~exphub.core.beamline.technique.TabKey` slots the single-crystal
technique uses, but their meaning is SANS-shaped:

  - ``setup``              — IPTS / sample metadata (no crystallography fields)
  - ``configure_q_range``  — set the I(Q) reduction Q-range / binning knobs
  - ``load_strategy``      — build / load the SANS instrument-configuration plan
  - ``monitor_reduction``  — watch the (placeholder) I(Q) reduction
  - ``save``               — save / submit and persist results

``field_prefixes`` scope which schema fields are relevant per phase; they are
provisional and match the SANS sub-models' field names (TBD with the SANS
scientist as the science is specified). Submission shares the EIC pipeline
(``MULTI_TECHNIQUE_PLAN.md`` decision #1), so the ``save`` phase lives on the
strategy (STEERING) tab where the EIC Control surface is, mirroring the
single-crystal ``submit`` phase placement.
"""

from __future__ import annotations

from ....core.beamline import PhaseDefinition, TabKey

# The 5 SANS phases in order.
SANS_PHASES: tuple[PhaseDefinition, ...] = (
    PhaseDefinition(
        name="setup",
        tab=TabKey.IPTS,
        label="IPTS Info",
        description="Enter experiment metadata: IPTS, instrument, sample info",
        field_prefixes=(
            "ipts_number",
            "exp_name",
            "instrument",
            "molecular_formula",
            "sample_environment",
        ),
    ),
    PhaseDefinition(
        name="configure_q_range",
        tab=TabKey.LIVE,
        label="I(Q) Reduction",
        description="Configure the I(Q) reduction Q-range and binning",
        field_prefixes=(
            "q_min",
            "q_max",
            "n_q_bins",
            "prediction_model",
        ),
    ),
    PhaseDefinition(
        name="load_strategy",
        tab=TabKey.STEERING,
        label="Experiment Steering",
        description="Build or load the SANS instrument-configuration strategy",
        field_prefixes=(
            "plan_name",
            "plan_file",
            "sample_aperture",
            "detector_distance",
            "attenuator",
            "wavelength_spread",
        ),
    ),
    PhaseDefinition(
        name="monitor_reduction",
        tab=TabKey.LIVE,
        label="I(Q) Reduction",
        description="Monitor the (placeholder) I(Q) reduction of collected runs",
    ),
    PhaseDefinition(
        name="save",
        tab=TabKey.STEERING,
        label="EIC Control",
        description="Submit the SANS strategy to EIC and save results",
    ),
)

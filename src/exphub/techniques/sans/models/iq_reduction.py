"""SANS I(Q) reduction model (P4.1 placeholder).

The SANS analogue of the single-crystal
:class:`~exphub.techniques.single_crystal.models.data_analysis.DataAnalysisModel`.
Where single-crystal reduces events to integrated Bragg-peak intensities, SANS
reduces to an azimuthally-averaged I(Q) curve.

This is a PLACEHOLDER. No real Mantid SANS reduction pipeline is wired here yet
(per ``DECISION DEFAULTS`` in the P4 task brief): the prediction-model dropdown
stays ``"TBD"`` until the SANS pipeline is specified, and :meth:`get_figure`
returns an empty annotated figure rather than reduced data.
"""

from __future__ import annotations

import plotly.graph_objects as go
from pydantic import BaseModel, Field

# Provisional: real reduction / prediction backends are TBD with the SANS
# scientist. Only the placeholder option exists today.
PREDICTION_MODEL_OPTIONS = ["TBD"]


class SansIQReductionModel(BaseModel):
    """Placeholder configuration for SANS I(Q) reduction.

    Mirrors the single-crystal data-analysis model's output-directory surface
    so the SANS Data-Analysis tab can be built with the same idioms, but carries
    no real reduction parameters yet. ``prediction_model`` is pinned to ``"TBD"``
    until a SANS pipeline is specified.
    """

    # Output directories — populated by the active beamline + IPTS path resolver
    # once an IPTS number is provided (empty placeholder defaults, as in SC).
    output_dir: str = Field(default="", title="Output Directory")
    data_dir: str = Field(default="", title="Data Directory")
    output_dir_reduction: str = Field(default="", title="Output Directory for Reduction")

    # Prediction / reduction model selector. Stays "TBD" until a real SANS
    # pipeline (e.g. a Mantid I(Q) workflow) is specified.
    prediction_model: str = Field(default="TBD", title="Prediction Model")
    prediction_model_options: list[str] = Field(default_factory=lambda: list(PREDICTION_MODEL_OPTIONS))

    # Provisional Q-range knobs for the (future) reduction. Carried as plain
    # fields so the placeholder view has something to render; no pipeline reads
    # them yet.
    q_min: float = Field(default=0.001, title="Q-min (1/Angstrom)")
    q_max: float = Field(default=0.5, title="Q-max (1/Angstrom)")
    n_q_bins: int = Field(default=100, title="Number of Q bins")

    def get_figure(self) -> go.Figure:
        """Return an empty, annotated placeholder I(Q) figure.

        No reduction is performed; this draws a log-log axis frame with a
        "reduction pipeline TBD" annotation so the tab renders something
        meaningful before the SANS pipeline lands.
        """
        figure = go.Figure()
        figure.update_layout(
            title={"text": "SANS I(Q) — reduction pipeline TBD"},
            xaxis={"title": {"text": "Q (1/Angstrom)"}, "type": "log"},
            yaxis={"title": {"text": "I(Q)"}, "type": "log"},
            annotations=[
                {
                    "text": "SANS reduction not yet wired (prediction_model = 'TBD')",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                }
            ],
        )
        return figure

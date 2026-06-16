"""SANS IPTS-Info tab view (P4.2).

The SANS analogue of the single-crystal
:class:`~exphub.techniques.single_crystal.views.experiment_info.ExperimentInfoView`,
reduced to *sample-info fields only*. There is no crystal-system / point-group /
centering row and no UB / d-spacing block — SANS has no reciprocal lattice. What
remains is the shared experiment-identity surface plus a SANS sample-environment
selector.

Binds to the SANS steering VM's ``iptsinfo_bind`` under the ``config`` namespace,
matching the single-crystal view's idiom so the dispatcher can construct it the
same way.
"""

from nova.trame.view.components import InputField
from nova.trame.view.layouts import GridLayout

from ..view_models.steering import SansSteeringViewModel


class SansIptsInfoView:
    """View class to render the SANS IPTS-Info tab."""

    def __init__(self, view_model: SansSteeringViewModel) -> None:
        self.view_model = view_model
        self.view_model.iptsinfo_bind.connect("config")
        self.create_ui()

    def create_ui(self) -> None:
        with GridLayout(columns=2, gap="0.5em"):
            InputField(v_model="config.exp_name")
            InputField(v_model="config.ipts_number")
            InputField(v_model="config.instrument", items="config.options.instrument_list", type="select")

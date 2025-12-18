"""Module for the CSS Status tab."""

from nova.trame.view.components import InputField
from nova.trame.view.layouts import VBoxLayout

from ..view_models.main import MainViewModel


class CSSStatusView:
    """View class for Plotly."""

    def __init__(self, view_model: MainViewModel) -> None:
        self.view_model = view_model
        self.view_model.cssstatus_bind.connect("model_cssstatus")
        self.create_ui()
        self.view_model.update_cssstatus_figure()

    def create_ui(self) -> None:
        with VBoxLayout(columns=1):
            InputField(v_model="model_cssstatus.plot_type", items="model_cssstatus.plot_type_options", type="select")

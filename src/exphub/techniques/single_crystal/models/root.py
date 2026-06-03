"""Single-crystal technique root model.

Composes the single-crystal sub-models (experiment info, angle plan, EIC
control, CSS status, temporal analysis, data analysis) into a single Pydantic
root, mirroring the role :class:`~exphub.techniques.sans.models.root.SansMainModel`
plays for SANS. Wired as the single-crystal manifest's ``root_model_factory``.

Moved out of ``app/models/main_model.py`` and renamed ``MainModel`` →
``SingleCrystalMainModel`` during the multi-technique refactor.
"""

from pydantic import BaseModel, Field

from ....core.eic import EICControlModel
from .angle_plan import AnglePlanModel
from .css_status import CSSStatusModel
from .data_analysis import DataAnalysisModel
from .experiment_info import ExperimentInfoModel
from .newtabtemplate import NewTabTemplateModel
from .temporal_analysis import TemporalAnalysisModel


class SingleCrystalMainModel(BaseModel):
    """
    A model class.

    This class uses Pydantic (https://docs.pydantic.dev/latest/),
    which allows for defining data validation rules,
    titles, descriptions, and examples that can be used in GUI elements or
    other interfaces for improved clarity and usability.
    """

    username: str = Field(
        default="test_name",
        min_length=1,
        title="User Name",
        description="Please provide the name of the user",
        examples=["user"],
    )
    password: str = Field(default="test_password", title="User Password")
    angleplan: AnglePlanModel = Field(default_factory=AnglePlanModel, title="Angle Plan")
    eiccontrol: EICControlModel = Field(default_factory=EICControlModel, title="EIC Control")
    experimentinfo: ExperimentInfoModel = Field(default_factory=ExperimentInfoModel, title="Experiment Info")
    cssstatus: CSSStatusModel = Field(default_factory=CSSStatusModel, title="CSS Status")
    temporalanalysis: TemporalAnalysisModel = Field(default_factory=TemporalAnalysisModel, title="Temporal Analysis")
    dataanalysis: DataAnalysisModel = Field(default_factory=DataAnalysisModel, title="Data Analysis")

    newtabtemplate: NewTabTemplateModel = Field(default_factory=NewTabTemplateModel, title="New Tab Template")
    # plotly: PlotlyModel = Field(default_factory=PlotlyModel, title="Plotly")

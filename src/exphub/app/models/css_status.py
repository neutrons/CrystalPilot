"""Model for CSS status."""

from typing import Dict, List

import plotly.graph_objects as go
from plotly.data import iris
from pydantic import BaseModel, Field

IRIS_DATA = iris()


bl12cssstatus_urlsrc = "https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D"


class CSSStatusModel(BaseModel):
    """Pydantic class for CSS status."""

    table_test: List[Dict] = Field(default=[{"title": "1", "header": "h"}])
    angle_list: List[Dict] = Field(
        default=[
            {
                "Title": "test_angleplan_1",
                "Comment": "",
                "BL12:Mot:goniokm:phi": 0,
                "BL12:Mot:goniokm:omega": 0,
                "Wait For": "PCharge",
                "Value": 10,
            }
        ]
    )
    plan_file: str = Field(default="angle_plan.csv")
    plan_file_list: List[str] = Field(default=["angle_plan.csv"])

    axis_options: list[str] = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
    x_axis: str = Field(default="sepal_length", title="X Axis")
    y_axis: str = Field(default="sepal_width", title="Y Axis")
    z_axis: str = Field(default="petal_length", title="Color")
    plot_type: str = Field(default="Detector", title="Plot Type")
    # plot_type: str = Field(default="Preview", title="Plot Type")
    # plot_type_options: list[str] = ["heatmap", "scatter"]
    plot_type_options: list[str] = ["Detector", "D-space"]
    # init_image: bytes = save_webpage_as_image(bl12cssstatus_urlsrc)
    # plot_type_options: list[str] = ["Detector", "D-space", "Q-space", "4x4 and ROI D-space", "ROI Q-space", "IOCSTATS", "Det", "N1", "Main Detector", "N1", "BL12", "DID", "S"] # noqa
    # fig: go.Figure = Field(default=go.Figure(), title="Figure")
    screenshot: str = Field(default="")

    # @computed_field  # type: ignore
    # @property
    # def get_css_status(self) -> str:
    timestamp: float = Field(default=0.0, title="timestamp")

    def is_not_heatmap(self) -> bool:
        match self.plot_type:
            case "heatmap":
                return False
            case _:
                return True

    def get_figure_0(self) -> go.Figure:
        match self.plot_type:
            case "heatmap":
                plot_data = go.Heatmap(
                    x=IRIS_DATA[self.x_axis].tolist(),
                    y=IRIS_DATA[self.y_axis].tolist(),
                    z=IRIS_DATA[self.z_axis].tolist(),
                )

            case "scatter":
                plot_data = go.Scatter(
                    x=IRIS_DATA[self.x_axis].tolist(), y=IRIS_DATA[self.y_axis].tolist(), mode="markers"
                )
            case _:
                raise ValueError(f"Invalid plot type: {self.plot_type}")

        figure = go.Figure(plot_data)
        figure.update_layout(
            title={"text": f"{self.plot_type}"},
            xaxis={"title": {"text": self.x_axis}},
            yaxis={"title": {"text": self.y_axis}},
        )

        return figure

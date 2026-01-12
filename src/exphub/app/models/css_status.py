"""Model for CSS status."""

from typing import Any, Dict

from pydantic import BaseModel, Field

# TODO: remove this, just for reference
bl12cssstatus_urlsrc = "https://status.sns.ornl.gov/dbwr/view.jsp?display=https%3A//webopi.sns.gov/bl12/files/bl12/opi/BL12_ADnED_2D_4x4.bob&macros=%7B%26quot%3BDET1%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BDET2%26quot%3B%3A%26quot%3BMain%20d-Space%26quot%3B%2C%26quot%3BDET3%26quot%3B%3A%26quot%3BMain%20q-Space%26quot%3B%2C%26quot%3BDET4%26quot%3B%3A%26quot%3BMain%204x4%20and%20ROI%20d-Space%26quot%3B%2C%26quot%3BDET5%26quot%3B%3A%26quot%3BMain%20ROI%20q-Space%26quot%3B%2C%26quot%3BIOCSTATS%26quot%3B%3A%26quot%3BBL12%3ACS%3AADnED%3A%26quot%3B%2C%26quot%3BP%26quot%3B%3A%26quot%3BBL12%3ADet%3A%26quot%3B%2C%26quot%3BR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BTAB%26quot%3B%3A%26quot%3BMain%20Detector%26quot%3B%2C%26quot%3BTOPR%26quot%3B%3A%26quot%3BN1%3A%26quot%3B%2C%26quot%3BBL%26quot%3B%3A%26quot%3BBL12%26quot%3B%2C%26quot%3BDID%26quot%3B%3A%26quot%3BDID305%26quot%3B%2C%26quot%3BS%26quot%3B%3A%26quot%3BBL12%26quot%3B%7D"


class CSSStatusModel(BaseModel):
    """Pydantic class for CSS status."""

    active_plot: str = Field(default="0")
    active_details_plot: str = Field(default="3")

    # TODO: would like a better way to handle this.
    pv_data: Dict[str, Any] = Field(default={})

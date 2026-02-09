"""Model for CSS status."""

from typing import Any, Dict

from pydantic import BaseModel, Field


class CSSStatusModel(BaseModel):
    """Pydantic class for CSS status."""

    active_details_plot: str = Field(default="3")

    pv_data: Dict[str, Any] = Field(default={})

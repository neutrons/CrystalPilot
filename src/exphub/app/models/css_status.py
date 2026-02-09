"""Model for CSS status."""

from pydantic import BaseModel, Field


class CSSStatusModel(BaseModel):
    """Pydantic class for CSS status."""

    active_details_plot: str = Field(default="3")

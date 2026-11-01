from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Request base: unknown fields are a 422, so a typo is never silently ignored."""

    model_config = ConfigDict(extra="forbid")

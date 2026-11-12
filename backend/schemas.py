"""Validated request and response models for Project Sentinel."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictionRequest(BaseModel):
    """The exact three-feature input schema saved with the trained model."""

    model_config = ConfigDict(extra="forbid")

    absolute_magnitude: float = Field(description="Absolute magnitude (mag).")
    relative_velocity: float = Field(description="Relative velocity (km/h).")
    miss_distance: float = Field(description="Miss distance (km).")

    @field_validator("absolute_magnitude", "relative_velocity", "miss_distance")
    @classmethod
    def require_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("must be a finite number")
        return value

    @field_validator("relative_velocity", "miss_distance")
    @classmethod
    def require_nonnegative_distance_or_speed(cls, value: float) -> float:
        if value < 0:
            raise ValueError("must not be negative")
        return value


class HealthResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    model_ready: bool
    detail: str | None = None


class PredictionResponse(BaseModel):
    predicted_hazardous: bool
    classification: str
    model_score: float
    threshold: float
    model_version: str
    score_interpretation: str
    limitation: str


class ModelInfoResponse(BaseModel):
    ready: bool
    model_name: str | None = None
    model_version: str | None = None
    algorithm: str | None = None
    sklearn_version: str | None = None
    required_features: list[str] = Field(default_factory=list)
    units: dict[str, str] = Field(default_factory=dict)
    classification_threshold: float | None = None
    prediction_task: str | None = None
    impact_prediction: bool = False
    verified_metrics: dict[str, float] | None = None
    limitation: str


class AsteroidRecord(BaseModel):
    id: str
    name: str
    absolute_magnitude: float | None
    est_diameter_min: float | None
    est_diameter_max: float | None
    relative_velocity: float | None
    miss_distance: float | None
    hazardous: bool | None


class AsteroidPage(BaseModel):
    items: list[AsteroidRecord]
    total: int
    offset: int
    limit: int
    source: str

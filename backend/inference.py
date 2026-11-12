"""Trusted-artifact loading and inference helpers for Project Sentinel."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import Settings


REQUIRED_METADATA_KEYS = {
    "model_name",
    "model_version",
    "algorithm",
    "features",
    "threshold",
    "sklearn_version",
    "prediction_task",
    "impact_prediction",
    "units",
}


class ModelUnavailableError(RuntimeError):
    """Raised when the audited model is not available for safe inference."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ModelUnavailableError("Model metadata file is missing.")
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ModelUnavailableError("Model metadata could not be read.") from error

    if not isinstance(metadata, dict) or not REQUIRED_METADATA_KEYS.issubset(metadata):
        raise ModelUnavailableError("Model metadata does not contain the required deployment contract.")
    if not isinstance(metadata["features"], list) or not all(isinstance(item, str) for item in metadata["features"]):
        raise ModelUnavailableError("Model metadata has an invalid feature list.")
    if not isinstance(metadata["threshold"], (int, float)) or not 0 <= metadata["threshold"] <= 1:
        raise ModelUnavailableError("Model metadata has an invalid classification threshold.")
    return metadata


class ModelService:
    """Loads one known-hash artifact and applies its persisted prediction contract."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model: Any | None = None
        self.metadata: dict[str, Any] | None = None
        self.unavailable_reason: str | None = None

    @property
    def ready(self) -> bool:
        return self.model is not None and self.metadata is not None

    def startup(self) -> None:
        """Verify and load the user-provided artifact once at application startup."""
        self.model = None
        self.metadata = None
        self.unavailable_reason = None
        try:
            model_path = self.settings.model_path.resolve(strict=True)
            if not model_path.is_file():
                raise ModelUnavailableError("Configured model path is not a regular file.")
            actual_hash = sha256_file(model_path)
            if not self.settings.model_sha256 or actual_hash != self.settings.model_sha256:
                raise ModelUnavailableError("Configured model SHA-256 does not match the audited artifact.")

            metadata = _load_metadata(self.settings.metadata_path)
            # joblib/pickle files can execute code while loading. The hash check
            # above deliberately limits loading to the audited artifact only.
            model = joblib.load(model_path)
            saved_features = list(getattr(model, "feature_names_in_", []))
            if saved_features != metadata["features"]:
                raise ModelUnavailableError("Saved model feature order does not match model metadata.")
            if getattr(model, "n_features_in_", None) != len(metadata["features"]):
                raise ModelUnavailableError("Saved model input width does not match model metadata.")
            if not callable(getattr(model, "predict_proba", None)):
                raise ModelUnavailableError("Saved model does not support probability scores.")
            classes = list(getattr(model, "classes_", []))
            if 1 not in classes:
                raise ModelUnavailableError("Saved model does not expose a hazardous class label of 1.")

            self.model = model
            self.metadata = metadata
        except (ModelUnavailableError, FileNotFoundError, OSError, ValueError, TypeError, AttributeError) as error:
            self.unavailable_reason = str(error)
        except Exception:
            # Do not leak internal artifact-loading details to clients.
            self.unavailable_reason = "The audited model could not be loaded with the configured runtime."

    def require_ready(self) -> None:
        if not self.ready:
            raise ModelUnavailableError(self.unavailable_reason or "The model is unavailable.")

    @property
    def features(self) -> list[str]:
        self.require_ready()
        assert self.metadata is not None
        return list(self.metadata["features"])

    def predict(self, values: dict[str, float]) -> dict[str, Any]:
        """Score one validated row exactly once and apply the persisted threshold."""
        self.require_ready()
        assert self.model is not None and self.metadata is not None
        features = self.features
        frame = pd.DataFrame([[values[name] for name in features]], columns=features)
        probabilities = self.model.predict_proba(frame)  # exactly one model score call
        classes = list(self.model.classes_)
        hazardous_index = classes.index(1)
        score = float(probabilities[0][hazardous_index])
        if not math.isfinite(score):
            raise ModelUnavailableError("The model produced a non-finite class score.")
        threshold = float(self.metadata["threshold"])
        return {
            "predicted_hazardous": score >= threshold,
            "model_score": score,
            "threshold": threshold,
            "model_version": self.metadata["model_version"],
        }


class AsteroidCatalog:
    """Read-only access to the supplied NASA NEO CSV."""

    REQUIRED_COLUMNS = {
        "id", "name", "est_diameter_min", "est_diameter_max",
        "relative_velocity", "miss_distance", "absolute_magnitude", "hazardous",
    }
    SAFE_SORTS = {"id", "name", "absolute_magnitude", "relative_velocity", "miss_distance"}

    def __init__(self, dataset_path: Path):
        self.dataset_path = dataset_path
        self.frame: pd.DataFrame | None = None
        self.unavailable_reason: str | None = None

    @property
    def ready(self) -> bool:
        return self.frame is not None

    def startup(self) -> None:
        self.frame = None
        self.unavailable_reason = None
        try:
            dataset_path = self.dataset_path.resolve(strict=True)
            frame = pd.read_csv(dataset_path)
            if not self.REQUIRED_COLUMNS.issubset(frame.columns):
                raise ValueError("Dataset does not contain the required catalogue columns.")
            frame = frame.copy()
            frame["id"] = frame["id"].astype(str)
            frame["name"] = frame["name"].astype(str)
            for column in ("absolute_magnitude", "est_diameter_min", "est_diameter_max", "relative_velocity", "miss_distance"):
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
            frame["hazardous"] = frame["hazardous"].map({True: True, False: False, "True": True, "False": False})
            self.frame = frame
        except (FileNotFoundError, OSError, ValueError, pd.errors.ParserError) as error:
            self.unavailable_reason = str(error)

    def page(self, *, offset: int, limit: int, hazardous: bool | None, query: str | None, sort_by: str, order: str) -> tuple[list[dict[str, Any]], int]:
        if self.frame is None:
            raise ModelUnavailableError(self.unavailable_reason or "The dataset is unavailable.")
        if sort_by not in self.SAFE_SORTS:
            raise ValueError("Unsupported sort field.")
        filtered = self.frame
        if hazardous is not None:
            filtered = filtered.loc[filtered["hazardous"] == hazardous]
        if query:
            filtered = filtered.loc[filtered["name"].str.contains(query, case=False, na=False, regex=False)]
        filtered = filtered.sort_values(sort_by, ascending=(order == "asc"), kind="mergesort")
        total = len(filtered)
        columns = ["id", "name", "absolute_magnitude", "est_diameter_min", "est_diameter_max", "relative_velocity", "miss_distance", "hazardous"]
        records = filtered.iloc[offset:offset + limit][columns].replace({np.nan: None}).to_dict(orient="records")
        return records, total

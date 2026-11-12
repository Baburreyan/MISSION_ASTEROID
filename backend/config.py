"""Configuration for a locally verified Project Sentinel deployment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS_ROOT = Path("/Users/baburreyan/Downloads")

# This is the SHA-256 recorded during the deployment audit for the user-supplied
# model. A deployer can replace it only by explicitly supplying a matching hash.
AUDITED_MODEL_SHA256 = "e5479eebbaec131087521b62b3eeb9ec07dd0ad44fdbc422f79411a71e0830d2"


@dataclass(frozen=True)
class Settings:
    """Runtime paths. Environment variables allow a deliberate local deployment."""

    model_path: Path
    metadata_path: Path
    dataset_path: Path
    model_sha256: str
    static_dir: Path = PROJECT_ROOT

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            model_path=Path(os.environ.get("SENTINEL_MODEL_PATH", DOWNLOADS_ROOT / "sentinel_model.joblib")),
            metadata_path=Path(os.environ.get("SENTINEL_METADATA_PATH", DOWNLOADS_ROOT / "model_metadata.json")),
            dataset_path=Path(os.environ.get("SENTINEL_DATASET_PATH", DOWNLOADS_ROOT / "neo (3).csv")),
            model_sha256=os.environ.get("SENTINEL_MODEL_SHA256", AUDITED_MODEL_SHA256).lower(),
        )

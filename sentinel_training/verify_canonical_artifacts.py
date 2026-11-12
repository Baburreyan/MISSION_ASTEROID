"""Non-training integrity checks for Project Sentinel's staged candidate."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sentinel_training.canonical_pipeline import (
    DEFAULT_DATASET_PATH,
    FEATURES,
    KNOWN_LEGACY_MODEL_SHA256,
    ROOT as PROJECT_ROOT,
    STAGING_DIR,
    sha256_file,
)


def ids(path: Path) -> set[int]:
    return {int(value) for value in path.read_text(encoding="utf-8").splitlines() if value}


def main() -> None:
    split_dir = PROJECT_ROOT / "sentinel_training" / "splits"
    train_ids = ids(split_dir / "train_asteroid_ids.txt")
    validation_ids = ids(split_dir / "validation_asteroid_ids.txt")
    test_ids = ids(split_dir / "test_asteroid_ids.txt")
    assert not train_ids & validation_ids
    assert not train_ids & test_ids
    assert not validation_ids & test_ids

    metadata = json.loads((STAGING_DIR / "sentinel_model_candidate_v1_1_0.metadata.json").read_text(encoding="utf-8"))
    fixture = json.loads((STAGING_DIR / "reference_prediction_fixture.json").read_text(encoding="utf-8"))
    model = joblib.load(STAGING_DIR / "sentinel_model_candidate_v1_1_0.joblib")
    assert tuple(model.feature_names_in_) == FEATURES
    assert tuple(metadata["features"]) == FEATURES
    assert metadata["status"] == "staged only; not active deployment artifact"
    assert fixture["legacy_model_sha256"] == KNOWN_LEGACY_MODEL_SHA256

    frame = pd.read_csv(DEFAULT_DATASET_PATH)
    X = pd.DataFrame([record["input"] for record in fixture["records"]], columns=list(FEATURES))
    expected = np.array([record["candidate_score"] for record in fixture["records"]])
    assert np.array_equal(model.predict_proba(X)[:, 1], expected)

    print(json.dumps({
        "status": "passed",
        "group_partitions_disjoint": True,
        "candidate_feature_order": list(model.feature_names_in_),
        "candidate_model_sha256": sha256_file(STAGING_DIR / "sentinel_model_candidate_v1_1_0.joblib"),
        "fixture_scores_reproduced": True,
        "dataset_rows_checked": int(len(frame)),
    }, indent=2))


if __name__ == "__main__":
    main()

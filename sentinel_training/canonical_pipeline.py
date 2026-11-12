"""Canonical, staged three-feature training pipeline for Project Sentinel.

This module intentionally writes only new provenance, split, and staging artifacts.
It never reads a legacy joblib file until its recorded SHA-256 has been verified and
never alters the deployed legacy artifact or its metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT.parent
TRAINING_ROOT = ROOT / "sentinel_training"
PROVENANCE_DIR = TRAINING_ROOT / "provenance"
SPLITS_DIR = TRAINING_ROOT / "splits"
STAGING_DIR = TRAINING_ROOT / "artifacts" / "staging"
CONFIG_PATH = TRAINING_ROOT / "canonical_training_config.json"
DEFAULT_DATASET_PATH = DOWNLOADS / "neo (3).csv"
DEFAULT_LEGACY_MODEL_PATH = DOWNLOADS / "sentinel_model.joblib"
DEFAULT_LEGACY_METADATA_PATH = DOWNLOADS / "model_metadata.json"

FEATURES = ("absolute_magnitude", "relative_velocity", "miss_distance")
TARGET = "hazardous"
GROUP = "id"
KNOWN_LEGACY_MODEL_SHA256 = "e5479eebbaec131087521b62b3eeb9ec07dd0ad44fdbc422f79411a71e0830d2"
MODEL_PARAMETERS = {
    "learning_rate": 0.03,
    "max_iter": 150,
    "max_leaf_nodes": 31,
    "l2_regularization": 5,
    "random_state": 42,
}
SEEDS = {"test_group_split": 42, "validation_group_split": 43, "model": 42, "permutation": 42}
UNITS = {
    "absolute_magnitude": {
        "value": "mag",
        "verification": "Declared in legacy deployment metadata; source-level CSV metadata was not supplied.",
    },
    "relative_velocity": {
        "value": "km/h",
        "verification": "Declared in legacy deployment metadata; source-level CSV metadata was not supplied.",
    },
    "miss_distance": {
        "value": "km",
        "verification": "Declared in legacy deployment metadata; source-level CSV metadata was not supplied.",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_deterministic(path: Path, content: bytes) -> None:
    """Create an output or verify an identical previous deterministic output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            old = path.read_bytes()
            if path.name == "canonical_training_report.json":
                diagnostic = path.with_name("canonical_training_report_rerun_diagnostic.json")
                diagnostic.write_bytes(content)
            raise RuntimeError(
                "Refusing to replace non-identical reproducibility artifact: "
                f"{path} (existing_sha256={sha256_bytes(old)}, new_sha256={sha256_bytes(content)})"
            )
        return
    path.write_bytes(content)


def write_json(path: Path, value: Any) -> None:
    write_deterministic(path, stable_json(value))


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_dataset(path: Path = DEFAULT_DATASET_PATH) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Canonical dataset was not found: {path}")
    frame = pd.read_csv(path)
    required = {GROUP, TARGET, *FEATURES}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Dataset lacks required columns: {missing}")
    if frame[list(FEATURES)].isna().any().any() or frame[TARGET].isna().any() or frame[GROUP].isna().any():
        raise ValueError("Canonical features, target, and asteroid ID must be non-missing.")
    numeric = frame[list(FEATURES)].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Canonical features contain non-finite values.")
    frame.loc[:, list(FEATURES)] = numeric
    frame[TARGET] = frame[TARGET].astype(bool)
    conflicts = frame.groupby(GROUP, sort=False)[TARGET].nunique()
    if (conflicts > 1).any():
        conflicting = conflicts[conflicts > 1].index[:5].tolist()
        raise ValueError(f"Asteroid IDs with inconsistent labels: {conflicting}")
    return frame


def dataset_provenance(frame: pd.DataFrame, path: Path) -> dict[str, Any]:
    numeric = frame.select_dtypes(include=[np.number])
    return {
        "dataset_path": str(path.resolve()),
        "sha256": sha256_file(path),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "missing_values": {column: int(value) for column, value in frame.isna().sum().items()},
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "unique_asteroid_ids": int(frame[GROUP].nunique()),
        "rows_with_repeated_asteroid_id": int(frame[GROUP].duplicated(keep=False).sum()),
        "asteroid_ids_with_repeated_observations": int((frame.groupby(GROUP).size() > 1).sum()),
        "target_distribution": {
            str(label): {"rows": int(count), "prevalence": float(count / len(frame))}
            for label, count in frame[TARGET].value_counts().sort_index().items()
        },
        "nonfinite_numeric_values": int((~np.isfinite(numeric.to_numpy(dtype=float))).sum()),
        "constant_columns": [column for column in frame.columns if frame[column].nunique(dropna=False) <= 1],
        "canonical_feature_units": UNITS,
        "provenance_limitations": [
            "The provided CSV filename suggests NEO data, but a source URL, release/version, and field dictionary were not supplied.",
            "The hazardous label definition is not independently verified from source metadata.",
            "Declared units come from the legacy deployment metadata and remain unresolved at the CSV source level.",
        ],
    }


def legacy_preservation_manifest(model_path: Path, metadata_path: Path) -> dict[str, Any]:
    if not model_path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError("Legacy model and metadata must both be present for preservation audit.")
    model_hash = sha256_file(model_path)
    if model_hash != KNOWN_LEGACY_MODEL_SHA256:
        raise RuntimeError("Legacy model hash does not match the audited trusted artifact; it will not be loaded.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return {
        "legacy_version": "1.0.0",
        "status": "preserved; not modified, renamed, or used as the active candidate",
        "model_path": str(model_path.resolve()),
        "model_sha256": model_hash,
        "metadata_path": str(metadata_path.resolve()),
        "metadata_sha256": sha256_file(metadata_path),
        "metadata_snapshot": metadata,
    }


@dataclass(frozen=True)
class SplitResult:
    train_ids: np.ndarray
    validation_ids: np.ndarray
    test_ids: np.ndarray
    train_mask: pd.Series
    validation_mask: pd.Series
    test_mask: pd.Series
    manifest: dict[str, Any]


def _partition_summary(frame: pd.DataFrame, mask: pd.Series) -> dict[str, Any]:
    subset = frame.loc[mask]
    return {
        "rows": int(len(subset)),
        "unique_asteroid_ids": int(subset[GROUP].nunique()),
        "hazardous_rows": int(subset[TARGET].sum()),
        "hazardous_prevalence": float(subset[TARGET].mean()),
    }


def _write_manifest(name: str, ids: np.ndarray) -> dict[str, Any]:
    values = sorted(int(value) for value in ids)
    content = ("\n".join(str(value) for value in values) + "\n").encode("utf-8")
    path = SPLITS_DIR / f"{name}_asteroid_ids.txt"
    write_deterministic(path, content)
    return {"path": str(path.relative_to(ROOT)), "count": len(values), "sha256": sha256_bytes(content)}


def create_group_splits(frame: pd.DataFrame) -> SplitResult:
    """Create 60/20/20 row grouping via a 80/20 then 75/25 unique-ID split.

    Stratification happens at asteroid-ID level because all repeated observations for
    an ID have the same label. Row counts need not be exactly 60/20/20.
    """
    labels = frame.groupby(GROUP, sort=True)[TARGET].first()
    ids = labels.index.to_numpy()
    train_validation_ids, test_ids = train_test_split(
        ids, test_size=0.20, random_state=SEEDS["test_group_split"], stratify=labels.to_numpy()
    )
    train_validation_labels = labels.loc[train_validation_ids].to_numpy()
    train_ids, validation_ids = train_test_split(
        train_validation_ids,
        test_size=0.25,
        random_state=SEEDS["validation_group_split"],
        stratify=train_validation_labels,
    )
    train_set, validation_set, test_set = set(train_ids), set(validation_ids), set(test_ids)
    if train_set & validation_set or train_set & test_set or validation_set & test_set:
        raise AssertionError("Asteroid ID partitions overlap.")
    if train_set | validation_set | test_set != set(ids):
        raise AssertionError("Asteroid ID partitions do not cover the dataset.")
    train_mask = frame[GROUP].isin(train_set)
    validation_mask = frame[GROUP].isin(validation_set)
    test_mask = frame[GROUP].isin(test_set)
    manifests = {
        "train": _write_manifest("train", train_ids),
        "validation": _write_manifest("validation", validation_ids),
        "test": _write_manifest("test", test_ids),
    }
    manifest = {
        "method": "two-stage stratified split of unique asteroid IDs",
        "group_column": GROUP,
        "target_column": TARGET,
        "seeds": {"test_group_split": 42, "validation_group_split": 43},
        "integrity_checks": {
            "train_validation_disjoint": True,
            "train_test_disjoint": True,
            "validation_test_disjoint": True,
            "all_unique_ids_assigned_once": True,
            "same_id_target_conflicts": 0,
        },
        "manifests": manifests,
        "partitions": {
            "train": _partition_summary(frame, train_mask),
            "validation": _partition_summary(frame, validation_mask),
            "test": _partition_summary(frame, test_mask),
        },
        "interpretation_caveat": (
            "Earlier model-development work may have examined observations in this CSV. "
            "This deterministic split is a reproducibility benchmark, not a demonstrably untouched independent holdout."
        ),
    }
    write_json(SPLITS_DIR / "split_manifest.json", manifest)
    return SplitResult(train_ids, validation_ids, test_ids, train_mask, validation_mask, test_mask, manifest)


def feature_schema(frame: pd.DataFrame) -> list[dict[str, Any]]:
    schema = []
    for feature in FEATURES:
        values = frame[feature]
        schema.append(
            {
                "name": feature,
                "dtype": str(values.dtype),
                "unit": UNITS[feature]["value"],
                "unit_verification": UNITS[feature]["verification"],
                "required": True,
                "observed_min": float(values.min()),
                "observed_max": float(values.max()),
                "missing_values": int(values.isna().sum()),
                "validation_note": "Finite numeric value within the observed dataset bounds for benchmark input checks.",
            }
        )
    return schema


def train_model(frame: pd.DataFrame, splits: SplitResult) -> HistGradientBoostingClassifier:
    X_train = frame.loc[splits.train_mask, list(FEATURES)].copy()
    y_train = frame.loc[splits.train_mask, TARGET].astype(int)
    model = HistGradientBoostingClassifier(**MODEL_PARAMETERS)
    model.fit(X_train, y_train)
    if tuple(model.feature_names_in_) != FEATURES:
        raise AssertionError("Fitted candidate feature order differs from canonical schema.")
    return model


def choose_threshold(y_true: pd.Series, scores: np.ndarray) -> tuple[float, dict[str, Any]]:
    candidates: list[dict[str, float]] = []
    for threshold in np.unique(scores):
        predicted = (scores >= threshold).astype(int)
        candidates.append(
            {
                "threshold": float(threshold),
                "precision": float(precision_score(y_true, predicted, zero_division=0)),
                "hazardous_recall": float(recall_score(y_true, predicted, zero_division=0)),
                "f2": float(fbeta_score(y_true, predicted, beta=2, zero_division=0)),
            }
        )
    eligible = [candidate for candidate in candidates if candidate["hazardous_recall"] >= 0.95]
    pool = eligible or candidates
    selected = sorted(pool, key=lambda item: (-item["f2"], -item["precision"], item["threshold"]))[0]
    return selected["threshold"], {
        "method": "maximize F2 among thresholds with hazardous recall >= 0.95; deterministic ties prefer higher precision then lower threshold",
        "minimum_hazardous_recall": 0.95,
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "selected_validation_metrics": selected,
    }


def evaluate(y_true: pd.Series, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predicted = (scores >= threshold).astype(int)
    matrix = confusion_matrix(y_true, predicted, labels=[0, 1]).tolist()
    return {
        "rows": int(len(y_true)),
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "hazardous_recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "f2": float(fbeta_score(y_true, predicted, beta=2, zero_division=0)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predicted)),
        "confusion_matrix_labels": ["actual_non_hazardous", "actual_hazardous"],
        "confusion_matrix": matrix,
    }


def validation_permutation_importance(
    model: HistGradientBoostingClassifier, frame: pd.DataFrame, splits: SplitResult
) -> list[dict[str, float]]:
    X_validation = frame.loc[splits.validation_mask, list(FEATURES)]
    y_validation = frame.loc[splits.validation_mask, TARGET].astype(int)
    result = permutation_importance(
        model, X_validation, y_validation, scoring="average_precision", n_repeats=3, random_state=SEEDS["permutation"], n_jobs=1
    )
    return [
        {"feature": feature, "mean_pr_auc_decrease": float(mean), "std": float(std)}
        for feature, mean, std in sorted(
            zip(FEATURES, result.importances_mean, result.importances_std), key=lambda item: item[1], reverse=True
        )
    ]


def _load_trusted_legacy(path: Path) -> Any:
    if sha256_file(path) != KNOWN_LEGACY_MODEL_SHA256:
        raise RuntimeError("Will not load legacy joblib because its trusted SHA-256 did not match.")
    return joblib.load(path)


def reference_fixture(
    frame: pd.DataFrame,
    candidate: HistGradientBoostingClassifier,
    threshold: float,
    legacy_path: Path,
    legacy_metadata_path: Path,
) -> dict[str, Any]:
    legacy = _load_trusted_legacy(legacy_path)
    legacy_metadata = json.loads(legacy_metadata_path.read_text(encoding="utf-8"))
    expected = tuple(getattr(legacy, "feature_names_in_", ()))
    if expected != FEATURES or tuple(legacy_metadata.get("features", [])) != FEATURES:
        raise AssertionError("Legacy input schema is not the audited three-feature schema.")
    indices = [0, len(frame) // 2, len(frame) - 1]
    X = frame.loc[indices, list(FEATURES)].copy()
    candidate_scores = candidate.predict_proba(X)[:, 1]
    legacy_scores = legacy.predict_proba(X)[:, 1]
    records = []
    for source_index, row, candidate_score, legacy_score in zip(indices, X.to_dict("records"), candidate_scores, legacy_scores):
        records.append(
            {
                "source_row_index": int(source_index),
                "input": {name: float(value) for name, value in row.items()},
                "candidate_score": float(candidate_score),
                "candidate_label_at_selected_threshold": bool(candidate_score >= threshold),
                "legacy_score_at_legacy_threshold": float(legacy_score),
                "legacy_label_at_legacy_threshold": bool(legacy_score >= float(legacy_metadata["threshold"])),
            }
        )
    return {
        "purpose": "Deterministic regression fixture and comparison only; score equality is not expected without the missing legacy training provenance.",
        "legacy_model_sha256": KNOWN_LEGACY_MODEL_SHA256,
        "legacy_threshold": float(legacy_metadata["threshold"]),
        "candidate_threshold": float(threshold),
        "records": records,
    }


def stage_candidate(
    frame: pd.DataFrame,
    model: HistGradientBoostingClassifier,
    splits: SplitResult,
    threshold: float,
    threshold_details: dict[str, Any],
    validation_metrics: dict[str, Any],
    feature_importance: list[dict[str, float]],
    dataset_info: dict[str, Any],
    legacy_manifest: dict[str, Any],
    legacy_path: Path,
    legacy_metadata_path: Path,
) -> dict[str, Any]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    model_path = STAGING_DIR / "sentinel_model_candidate_v1_1_0.joblib"
    metadata_path = STAGING_DIR / "sentinel_model_candidate_v1_1_0.metadata.json"
    fixture_path = STAGING_DIR / "reference_prediction_fixture.json"
    report_path = STAGING_DIR / "canonical_training_report_v1_1_0.json"
    if model_path.exists():
        # Existing candidate must already be equivalent to this deterministic run.
        reloaded_existing = joblib.load(model_path)
        sample = frame.loc[[0, len(frame) // 2, len(frame) - 1], list(FEATURES)]
        if not np.array_equal(model.predict_proba(sample), reloaded_existing.predict_proba(sample)):
            raise RuntimeError("Existing staged candidate is not prediction-equivalent; refusing to replace it.")
    else:
        joblib.dump(model, model_path)
    reloaded = joblib.load(model_path)
    sample = frame.loc[[0, len(frame) // 2, len(frame) - 1], list(FEATURES)]
    reload_equal = bool(np.array_equal(model.predict_proba(sample), reloaded.predict_proba(sample)))
    if not reload_equal:
        raise AssertionError("Reloaded staged candidate did not reproduce reference scores exactly.")
    fixture = reference_fixture(frame, model, threshold, legacy_path, legacy_metadata_path)
    fixture["candidate_reload_predictions_identical"] = reload_equal
    write_json(fixture_path, fixture)
    metadata = {
        "model_name": "Project Sentinel staged candidate",
        "model_version": "1.1.0-reproducibility-benchmark",
        "status": "staged only; not active deployment artifact",
        "algorithm": "HistGradientBoostingClassifier",
        "sklearn_version": sklearn.__version__,
        "features": list(FEATURES),
        "feature_schema": feature_schema(frame),
        "model_parameters": MODEL_PARAMETERS,
        "threshold": threshold,
        "threshold_selection": threshold_details,
        "validation_metrics": validation_metrics,
        "test_metrics": "Not computed before final evaluation authorization; the test partition remains unscored by this script.",
        "dataset": {"sha256": dataset_info["sha256"], "rows": dataset_info["rows"]},
        "split_manifest": str((SPLITS_DIR / "split_manifest.json").relative_to(ROOT)),
        "split_manifest_sha256": sha256_file(SPLITS_DIR / "split_manifest.json"),
        "candidate_model_sha256": sha256_file(model_path),
        "legacy_comparison": {
            "legacy_version": "1.0.0",
            "legacy_model_sha256": legacy_manifest["model_sha256"],
            "note": "Scores are compared on deterministic shared inputs but equality is not expected because legacy training provenance is incomplete.",
        },
        "limitations": [
            "This estimates the historical hazardous label in the provided data, not collision or impact probability.",
            "CSV-level source metadata, unit provenance, and hazardous-label definition remain unresolved.",
            "This benchmark split may contain observations previously examined during model development and is not guaranteed to be an independent untouched holdout.",
            "The staged candidate is not connected to the running API or frontend.",
        ],
    }
    write_json(metadata_path, metadata)
    report = {
        "run_status": "completed_without_test_scoring",
        "python_version": sys.version,
        "platform": platform.platform(),
        "sklearn_version": sklearn.__version__,
        "dataset_provenance": dataset_info,
        "legacy_preservation": legacy_manifest,
        "split_summary": splits.manifest,
        "feature_schema": feature_schema(frame),
        "model_parameters": MODEL_PARAMETERS,
        "threshold": threshold,
        "threshold_selection": threshold_details,
        "validation_metrics": validation_metrics,
        "validation_feature_analysis": {
            "status": "not persisted in the canonical provenance record",
            "reason": "Permutation-importance resampling is exploratory and not required to reproduce the candidate fit, threshold, or validation metrics.",
        },
        "reference_fixture": str(fixture_path.relative_to(ROOT)),
        "staged_model": {
            "path": str(model_path.relative_to(ROOT)),
            "sha256": sha256_file(model_path),
            "reloaded_predictions_identical": reload_equal,
        },
        "test_partition_status": "Reserved and intentionally not evaluated until the final evaluation step is authorized.",
    }
    write_json(report_path, report)
    return {"model_path": model_path, "metadata_path": metadata_path, "fixture_path": fixture_path, "report_path": report_path, "report": report}


def run(dataset_path: Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    frame = load_dataset(dataset_path)
    dataset_info = dataset_provenance(frame, dataset_path)
    write_json(PROVENANCE_DIR / "dataset_provenance.json", dataset_info)
    legacy_manifest = legacy_preservation_manifest(DEFAULT_LEGACY_MODEL_PATH, DEFAULT_LEGACY_METADATA_PATH)
    write_json(PROVENANCE_DIR / "legacy_v1_0_0_preservation.json", legacy_manifest)
    splits = create_group_splits(frame)
    model = train_model(frame, splits)
    X_validation = frame.loc[splits.validation_mask, list(FEATURES)]
    y_validation = frame.loc[splits.validation_mask, TARGET].astype(int)
    validation_scores = model.predict_proba(X_validation)[:, 1]
    threshold, threshold_details = choose_threshold(y_validation, validation_scores)
    validation_metrics = evaluate(y_validation, validation_scores, threshold)
    # Permutation importance is available as a validation-only exploratory helper,
    # but is deliberately not persisted in the reproducibility contract.
    importance: list[dict[str, float]] = []
    staged = stage_candidate(
        frame, model, splits, threshold, threshold_details, validation_metrics, importance,
        dataset_info, legacy_manifest, DEFAULT_LEGACY_MODEL_PATH, DEFAULT_LEGACY_METADATA_PATH,
    )
    return {
        "dataset": dataset_info,
        "splits": splits,
        "model": model,
        "threshold": threshold,
        "threshold_details": threshold_details,
        "validation_metrics": validation_metrics,
        "importance": importance,
        "staged": staged,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Project Sentinel's staged canonical candidate.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    args = parser.parse_args()
    outcome = run(args.dataset)
    summary = {
        "dataset_sha256": outcome["dataset"]["sha256"],
        "validation_metrics": outcome["validation_metrics"],
        "threshold": outcome["threshold"],
        "staged_report": str(outcome["staged"]["report_path"].relative_to(ROOT)),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

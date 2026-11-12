"""Integration tests against the audited Project Sentinel artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.config import AUDITED_MODEL_SHA256, Settings
from backend.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOWNLOADS = Path("/Users/baburreyan/Downloads")


def audited_settings() -> Settings:
    return Settings(
        model_path=DOWNLOADS / "sentinel_model.joblib",
        metadata_path=DOWNLOADS / "model_metadata.json",
        dataset_path=DOWNLOADS / "neo (3).csv",
        model_sha256=AUDITED_MODEL_SHA256,
        static_dir=PROJECT_ROOT,
    )


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(create_app(audited_settings())) as api_client:
        yield api_client


def sample_payload() -> dict[str, float]:
    row = pd.read_csv(DOWNLOADS / "neo (3).csv", nrows=1).iloc[0]
    return {
        "absolute_magnitude": float(row["absolute_magnitude"]),
        "relative_velocity": float(row["relative_velocity"]),
        "miss_distance": float(row["miss_distance"]),
    }


def test_successful_model_load_and_exact_feature_schema(client: TestClient) -> None:
    health = client.get("/api/health")
    info = client.get("/api/model-info")

    assert health.status_code == 200
    assert health.json() == {"status": "ready", "model_ready": True, "detail": None}
    assert info.status_code == 200
    body = info.json()
    assert body["algorithm"] == "HistGradientBoostingClassifier"
    assert body["model_version"] == "1.0.0"
    assert body["required_features"] == ["absolute_magnitude", "relative_velocity", "miss_distance"]
    assert body["units"] == {
        "absolute_magnitude": "mag",
        "relative_velocity": "km/h",
        "miss_distance": "km",
    }
    assert body["classification_threshold"] == 0.0815
    assert body["verified_metrics"] is None


def test_api_matches_saved_model_score_and_is_deterministic(client: TestClient) -> None:
    payload = sample_payload()
    first = client.post("/api/predict", json=payload)
    second = client.post("/api/predict", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()

    service = client.app.state.model_service
    frame = pd.DataFrame([[payload[name] for name in service.features]], columns=service.features)
    direct_score = float(service.model.predict_proba(frame)[0][list(service.model.classes_).index(1)])
    response = first.json()
    assert response["model_score"] == pytest.approx(direct_score)
    assert response["predicted_hazardous"] is (direct_score >= 0.0815)


def test_persisted_threshold_is_applied(client: TestClient) -> None:
    response = client.post("/api/predict", json=sample_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["threshold"] == 0.0815
    assert body["predicted_hazardous"] is (body["model_score"] >= body["threshold"])
    assert "impact" in body["limitation"].lower()
    assert "not a calibrated physical risk probability" in body["score_interpretation"]


@pytest.mark.parametrize(
    "payload",
    [
        {"absolute_magnitude": 22, "relative_velocity": 10},
        {"absolute_magnitude": 22, "relative_velocity": -1, "miss_distance": 10},
        {"absolute_magnitude": 22, "relative_velocity": 1, "miss_distance": -10},
        {"absolute_magnitude": 22, "relative_velocity": 1, "miss_distance": 10, "moid": 1},
    ],
)
def test_missing_invalid_and_extra_inputs_are_rejected(client: TestClient, payload: dict[str, float]) -> None:
    assert client.post("/api/predict", json=payload).status_code == 422


def test_nonfinite_input_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/predict",
        content='{"absolute_magnitude":22,"relative_velocity":NaN,"miss_distance":10}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_unavailable_model_has_a_clear_service_state(tmp_path: Path) -> None:
    settings = Settings(
        model_path=tmp_path / "missing.joblib",
        metadata_path=DOWNLOADS / "model_metadata.json",
        dataset_path=DOWNLOADS / "neo (3).csv",
        model_sha256=AUDITED_MODEL_SHA256,
        static_dir=PROJECT_ROOT,
    )
    with TestClient(create_app(settings)) as unavailable_client:
        health = unavailable_client.get("/api/health")
        prediction = unavailable_client.post("/api/predict", json=sample_payload())
    assert health.status_code == 200
    assert health.json()["status"] == "unavailable"
    assert "model" in health.json()["detail"].lower()
    assert prediction.status_code == 503


def test_real_catalogue_pagination_filter_and_total_count(client: TestClient) -> None:
    first = client.get("/api/asteroids", params={"limit": 2, "sort_by": "id"})
    second = client.get("/api/asteroids", params={"limit": 2, "offset": 2, "sort_by": "id"})
    hazardous = client.get("/api/asteroids", params={"limit": 3, "hazardous": "true"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert hazardous.status_code == 200
    assert first.json()["source"] == "neo (3).csv"
    assert first.json()["total"] == 90836
    assert len(first.json()["items"]) == 2
    assert first.json()["items"] != second.json()["items"]
    assert all(item["hazardous"] is True for item in hazardous.json()["items"])


def test_frontend_request_shape_matches_backend_contract() -> None:
    html = (PROJECT_ROOT / "code.html").read_text(encoding="utf-8")
    api_client = (PROJECT_ROOT / "sentinel-api.js").read_text(encoding="utf-8")
    for feature in ("absolute_magnitude", "relative_velocity", "miss_distance"):
        assert f'name="{feature}"' in html
        assert f"{feature}: Number(formData.get('{feature}'))" in html
    assert 'name="estimated_diameter"' not in html
    assert "POST" in api_client and "'/predict'" in api_client

# Project Sentinel local deployment

This service exposes the supplied, audited scikit-learn artifact through the existing static website. It performs historical hazardous-label classification only. It does **not** forecast an Earth impact or collision, and its returned score is a model class score—not a calibrated physical-risk probability.

## Verified artifact contract

- Model: `HistGradientBoostingClassifier`, Project Sentinel v1.0.0
- scikit-learn runtime: `1.6.1`
- Required ordered features: `absolute_magnitude` (mag), `relative_velocity` (km/h), `miss_distance` (km)
- Stored classification threshold: `0.0815`
- Artifact SHA-256: `e5479eebbaec131087521b62b3eeb9ec07dd0ad44fdbc422f79411a71e0830d2`

The model is loaded once at startup only after its SHA-256 equals the configured audited hash. `joblib` artifacts are deserialization-sensitive; do not replace the model file without separately validating it and deliberately setting a new `SENTINEL_MODEL_SHA256`.

## Run locally

From the Project Sentinel folder:

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
export SENTINEL_MODEL_PATH='/Users/baburreyan/Downloads/sentinel_model.joblib'
export SENTINEL_METADATA_PATH='/Users/baburreyan/Downloads/model_metadata.json'
export SENTINEL_DATASET_PATH='/Users/baburreyan/Downloads/neo (3).csv'
export SENTINEL_MODEL_SHA256='e5479eebbaec131087521b62b3eeb9ec07dd0ad44fdbc422f79411a71e0830d2'
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`—do not open `code.html` with `file://`. FastAPI defines `/api` routes before mounting static files, so the existing `sentinel-api.js` uses same-origin requests without a proxy or Node/React runtime. Direct file opens redirect to this local origin when the service is running.

## Endpoints

- `GET /api/health` — model readiness; this is the only endpoint that reports an unavailable model with HTTP 200.
- `GET /api/model-info` — model algorithm, version, saved feature contract, verified units, threshold, and no performance metrics unless saved metadata verifies them.
- `POST /api/predict` — validates exactly the saved three features, calls `predict_proba` once, and applies the stored threshold.
- `GET /api/asteroids?limit=25&offset=0&hazardous=true&sort_by=name&order=asc` — bounded (1–100) pagination over the local `neo (3).csv` dataset, with safe sorting and total count.

Example prediction:

```sh
curl -X POST http://127.0.0.1:8000/api/predict \
  -H 'Content-Type: application/json' \
  -d '{"absolute_magnitude":16.73,"relative_velocity":13569.2492241812,"miss_distance":54839744.08284605}'
```

## Test

```sh
.venv/bin/pytest backend/tests -q
```

The test suite checks model readiness, the exact saved schema, API/direct-model score agreement, threshold use, invalid and non-finite inputs, unavailable-model behavior, catalogue pagination, and the frontend request shape.

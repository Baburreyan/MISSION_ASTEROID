"""FastAPI entry point for the Project Sentinel local deployment."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .inference import AsteroidCatalog, ModelService, ModelUnavailableError
from .schemas import AsteroidPage, HealthResponse, ModelInfoResponse, PredictionRequest, PredictionResponse


LIMITATION = (
    "Historical hazardous-label classification only; this is not an Earth-impact or collision forecast."
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    model_service = ModelService(settings)
    catalog = AsteroidCatalog(settings.dataset_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        model_service.startup()
        catalog.startup()
        app.state.model_service = model_service
        app.state.catalog = catalog
        yield

    app = FastAPI(title="Project Sentinel API", version="1.0.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        # Strip raw submitted values from validation errors. Apart from avoiding
        # reflection of untrusted input, this keeps NaN/Infinity validation
        # errors JSON-serializable.
        details = [
            {key: value for key, value in item.items() if key not in {"input", "ctx"}}
            for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": details})

    def service(request: Request) -> ModelService:
        return request.app.state.model_service

    def catalogue(request: Request) -> AsteroidCatalog:
        return request.app.state.catalog

    @app.get("/api/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        current = service(request)
        if current.ready:
            return HealthResponse(status="ready", model_ready=True)
        return HealthResponse(status="unavailable", model_ready=False, detail=current.unavailable_reason)

    @app.get("/api/model-info", response_model=ModelInfoResponse)
    def model_info(request: Request) -> ModelInfoResponse:
        current = service(request)
        if not current.ready:
            raise HTTPException(status_code=503, detail=current.unavailable_reason or "The model is unavailable.")
        assert current.metadata is not None
        metadata = current.metadata
        return ModelInfoResponse(
            ready=True,
            model_name=metadata["model_name"],
            model_version=metadata["model_version"],
            algorithm=metadata["algorithm"],
            sklearn_version=metadata["sklearn_version"],
            required_features=current.features,
            units=metadata["units"],
            classification_threshold=metadata["threshold"],
            prediction_task=metadata["prediction_task"],
            impact_prediction=False,
            # The supplied metadata has no validated evaluation metrics.
            verified_metrics=None,
            limitation=LIMITATION,
        )

    @app.post("/api/predict", response_model=PredictionResponse)
    def predict(payload: PredictionRequest, request: Request) -> PredictionResponse:
        current = service(request)
        try:
            result = current.predict(payload.model_dump())
        except ModelUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return PredictionResponse(
            **result,
            classification=(
                "Predicted hazardous designation"
                if result["predicted_hazardous"]
                else "Predicted non-hazardous designation"
            ),
            score_interpretation="Model hazardous-class score; not a calibrated physical risk probability.",
            limitation=LIMITATION,
        )

    @app.get("/api/asteroids", response_model=AsteroidPage)
    def asteroids(
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(25, ge=1, le=100),
        hazardous: bool | None = Query(None),
        query: str | None = Query(None, min_length=1, max_length=100),
        sort_by: Literal["id", "name", "absolute_magnitude", "relative_velocity", "miss_distance"] = "name",
        order: Literal["asc", "desc"] = "asc",
    ) -> AsteroidPage:
        current_catalogue = catalogue(request)
        try:
            records, total = current_catalogue.page(
                offset=offset,
                limit=limit,
                hazardous=hazardous,
                query=query,
                sort_by=sort_by,
                order=order,
            )
        except ModelUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return AsteroidPage(items=records, total=total, offset=offset, limit=limit, source="neo (3).csv")

    @app.get("/", include_in_schema=False)
    def frontend() -> FileResponse:
        return FileResponse(Path(settings.static_dir) / "code.html")

    # This mount is intentionally last so /api routes always take precedence.
    app.mount("/", StaticFiles(directory=settings.static_dir, html=False), name="frontend-static")
    return app


app = create_app()

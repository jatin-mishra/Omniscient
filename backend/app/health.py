import asyncio
from typing import Annotated, Literal

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine
from temporalio.client import Client

from app.config import Settings, get_settings
from app.db import postgres
from app.db.deps import get_engine, get_es
from app.retrieval.deps import get_temporal_client
from app.retrieval.temporal.client import ping_temporal

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, bool]


@router.get("/health", response_model=HealthResponse)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, environment=settings.environment)


@router.get("/health/ready")
async def readiness(
    response: Response,
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    es: Annotated[AsyncElasticsearch, Depends(get_es)],
    temporal: Annotated[Client, Depends(get_temporal_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    is_postgres_up, is_es_up, is_temporal_up = await asyncio.gather(
        postgres.ping_postgres(engine),
        es.ping(),
        ping_temporal(temporal, settings.temporal_connect_timeout_s),
    )
    checks = {
        "postgres": is_postgres_up,
        "elasticsearch": is_es_up,
        "temporal": is_temporal_up,
    }
    is_ready = all(checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="ready" if is_ready else "not_ready", checks=checks)

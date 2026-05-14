"""
EchoFrame France Subrental — FastAPI entrypoint.

Wires routers, sets up CORS, runs the DB seeder on first boot, and
prefetches zone forecasts in the background so the first user request
returns from cache instead of triggering the full pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from api.data_sources_routes import router as data_sources_router
from api.documents_routes import router as documents_router
from api.finance_routes import router as finance_router
from api.forecast_routes import router as forecast_router
from api.market_routes import router as market_router
from api.meetings_routes import router as meetings_router
from api.milestones_routes import router as milestones_router
from api.narrative_routes import router as narrative_router
from api.ops_routes import router as ops_router
from api.owners_routes import router as owners_router
from api.pipeline_routes import router as pipeline_router
from api.signals_routes import router as signals_router
from config import settings
from data.property_seeder import seed_operational_tables_if_empty
from database import init_db
from services.forecast_service import forecast_service


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== EchoFrame France Subrental · starting ===")
    init_db()
    logger.info("Database tables ensured.")
    try:
        seed_operational_tables_if_empty()
        logger.info("Operational seed loaded.")
    except Exception as exc:
        logger.warning("Operational seed failed: %s", exc)

    # Fire-and-forget forecast prefetch so we don't block uvicorn.
    async def _prefetch() -> None:
        try:
            forecasts = await forecast_service.get_all_zone_forecasts()
            logger.info("Pre-fetched %d zone forecasts.", len(forecasts))
        except Exception as exc:
            logger.warning("Background prefetch failed: %s", exc)

    asyncio.create_task(_prefetch())
    logger.info("API listening on %s:%s", settings.api_host, settings.api_port)
    yield
    logger.info("=== shutting down ===")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, **settings.get_cors_settings())
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_cache_control(request: Request, call_next):
    """Short browser cache on GETs for read-only API surface."""
    response = await call_next(request)
    if request.method != "GET":
        response.headers.setdefault("Cache-Control", "no-store")
        return response
    if response.status_code >= 400:
        return response
    path = request.url.path
    if any(path.startswith(p) for p in ("/api/zones", "/api/communes", "/api/market", "/api/signals")):
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=240"
    return response


def _cors_headers(request: Request) -> dict:
    """Compute Access-Control-Allow-Origin for error responses."""
    origin = request.headers.get("origin")
    if not origin:
        return {}
    if "*" in settings.cors_origins or origin in settings.cors_origins:
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=_cors_headers(request),
        content={"error": {"code": exc.status_code, "message": exc.detail,
                            "timestamp": datetime.utcnow().isoformat()}},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    detail = "Internal server error" if settings.is_production() else str(exc)
    return JSONResponse(
        status_code=500,
        headers=_cors_headers(request),
        content={"error": {"code": 500, "message": detail,
                            "timestamp": datetime.utcnow().isoformat()}},
    )


# Routers
app.include_router(forecast_router)
app.include_router(market_router)
app.include_router(owners_router)
app.include_router(pipeline_router)
app.include_router(finance_router)
app.include_router(ops_router)
app.include_router(milestones_router)
app.include_router(meetings_router)
app.include_router(documents_router)
app.include_router(signals_router)
app.include_router(narrative_router)
app.include_router(data_sources_router)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

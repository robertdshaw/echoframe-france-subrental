"""
Data-source status route — surfaces which feeds are live vs falling
back to seeds. Powers the data-provenance ribbon in the sidebar.
"""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter

from config import settings
from data.airbnb_scraper import DEFAULT_ACTOR_ID, LIMIT_PER_ZONE, ZONE_SEARCH_TERMS
from data.apify_client import apify_client


router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])


@router.get("/status")
async def status():
    """One-call summary the frontend renders as 'live · seed · n/a' chips."""
    return {
        "checked_at": datetime.utcnow().isoformat(),
        "sources": [
            {
                "key": "insee",
                "name": "INSEE Melodi",
                "description": "Housing stock, population, vacancy, tourism",
                "status": "live (authenticated)" if settings.insee_api_key else "live (anonymous · 30 req/min)",
                "cost": "free (keyless tier available)",
                "endpoint": "api.insee.fr/melodi",
            },
            {
                "key": "bdf",
                "name": "Banque de France WebStat",
                "description": "Mortgage rates, EURIBOR, consumer credit",
                "status": "live" if settings.bdf_api_key else "seed_fallback",
                "cost": "free (key required since 2024 API migration)",
                "endpoint": "webstat.banque-france.fr/api/explore/v2.1",
            },
            {
                "key": "newsdata",
                "name": "NewsData.io",
                "description": "French-language news headlines",
                "status": "live" if settings.newsdata_api_key else "seed_fallback",
                "cost": "free 200 req/day, paid tiers above",
                "endpoint": "newsdata.io",
            },
            {
                "key": "datagouv",
                "name": "data.gouv.fr",
                "description": "DPE class distribution, DVF prices",
                "status": "live",
                "cost": "free (public)",
                "endpoint": "data.gouv.fr · data.ademe.fr",
            },
            {
                "key": "osm",
                "name": "OpenStreetMap",
                "description": "Geocoding + commune boundaries",
                "status": "live",
                "cost": "free (1 req/s)",
                "endpoint": "nominatim.openstreetmap.org",
            },
            {
                "key": "airbnb",
                "name": "Airbnb listings (Apify scrape)",
                "description": "Real comp listings with lat/lng/price/rating, 25 per zone, 24h disk cache",
                "status": "live" if os.environ.get("APIFY_TOKEN") else "seed_fallback",
                "cost": "$0.50 per 1k results · ~$2.60/mo at our volume (cache-limited)",
                "endpoint": "api.apify.com/v2 · actor tri_angle/new-fast-airbnb-scraper · token via APIFY_TOKEN",
            },
            {
                "key": "seloger",
                "name": "SeLoger + LeBonCoin (scrape)",
                "description": "Long-term rental asking prices",
                "status": "seed_fallback",
                "cost": "scrape (best-effort)",
                "endpoint": "seloger.com · leboncoin.fr",
            },
            {
                "key": "airroi",
                "name": "AirROI",
                "description": "Primary STR benchmark — ADR · occupancy · RevPAR · monthly revenue, 5/7 zones covered",
                "status": "live" if (os.environ.get("AIRROI_API_KEY") or os.environ.get("AIRROI_BEARER")) else "not_configured",
                "cost": "pay-as-you-go · $0.01/call · $10 minimum top-up (~$10/mo at our volume)",
                "endpoint": "api.airroi.com/v1 · X-API-KEY via AIRROI_API_KEY · key self-serve at airroi.com/api/developer/activate",
            },
            {
                "key": "airdna",
                "name": "AirDNA Enterprise (optional)",
                "description": "Fallback for zones AirROI misses (Pays de Gex, Geneva periphery). Not currently needed.",
                "status": "live" if os.environ.get("AIRDNA_BEARER") else "not_configured",
                "cost": "paid · Enterprise tier · ~30× AirROI cost · only enable if AirROI gap is blocking",
                "endpoint": "api.airdna.co/api/enterprise/v2 · Bearer via AIRDNA_BEARER",
            },
            {
                "key": "regulation",
                "name": "Regulation register",
                "description": "Meublé touristique flags + DPE + 120-day cap per commune",
                "status": "seed_fallback",
                "cost": "free (curated)",
                "endpoint": "data.gouv.fr · mairie websites",
            },
            {
                "key": "anthropic",
                "name": "Claude API",
                "description": "Narrative briefing language polish",
                "status": "live" if settings.anthropic_api_key else "deterministic_only",
                "cost": "metered, €50/mo cap",
                "endpoint": "api.anthropic.com",
            },
            {
                "key": "meteofrance",
                "name": "Météo-France",
                "description": "Weather forecasts + climatological normals · critical for ski-zone occupancy projection",
                "status": "live" if os.environ.get("METEOFRANCE_API_KEY") else "not_configured",
                "cost": "free (registration only)",
                "endpoint": "portail-api.meteofrance.fr",
            },
            {
                "key": "dvf",
                "name": "DVF (Demandes de Valeurs Foncières)",
                "description": "Real French property transaction prices since 2014 · sanity-check landlord asking rents",
                "status": "live",
                "cost": "free (public)",
                "endpoint": "app.dvf.etalab.gouv.fr",
            },
            {
                "key": "eurostat",
                "name": "Eurostat",
                "description": "EU tourism + housing benchmarks · cross-border context",
                "status": "live",
                "cost": "free (public)",
                "endpoint": "ec.europa.eu/eurostat",
            },
        ],
    }


@router.get("/airbnb-diagnose")
async def airbnb_diagnose():
    """Run a tiny Apify probe and return the raw result for debugging.

    Hit this when the comp map shows seed data and you want to know
    why Apify isn't kicking in. The endpoint runs a minimal scrape
    (2 listings, Lyon) and returns the actual HTTP status, error body,
    and a sample item so you can see exactly what's failing without
    grepping Render logs.
    """
    actor_id = os.environ.get("APIFY_AIRBNB_ACTOR_ID", DEFAULT_ACTOR_ID)
    probe_input = {
        "locationQueries": ["Lyon"],
        "maxItems": 2,
        "currency": "EUR",
    }
    started = datetime.utcnow()
    result = await apify_client.run_actor_sync_debug(actor_id, probe_input, timeout=60.0)
    elapsed_ms = int((datetime.utcnow() - started).total_seconds() * 1000)

    sample = None
    if result.get("data"):
        first = result["data"][0]
        if isinstance(first, dict):
            sample = {
                "id": first.get("id"),
                "name": first.get("name"),
                "url": first.get("url"),
                "roomType": first.get("roomType"),
                "personCapacity": first.get("personCapacity"),
                "coordinates": first.get("coordinates"),
                "pricing": first.get("pricing"),
                "rating": first.get("rating"),
            }

    return {
        "checked_at": datetime.utcnow().isoformat(),
        "elapsed_ms": elapsed_ms,
        "actor_id_used": result.get("actor_id"),
        "token_present": result.get("token_present"),
        "ok": result.get("ok"),
        "http_status": result.get("http_status"),
        "error": result.get("error"),
        "error_body_excerpt": result.get("error_body_excerpt"),
        "items_returned": len(result["data"]) if result.get("data") else 0,
        "sample_item": sample,
        "probe_input": probe_input,
        "configured": {
            "limit_per_zone": LIMIT_PER_ZONE,
            "zones_with_search_terms": list(ZONE_SEARCH_TERMS.keys()),
        },
    }

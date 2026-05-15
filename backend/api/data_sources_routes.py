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
    """One-call summary the frontend renders as 'live · seed · n/a' chips.

    `wired` = an API route actually consumes this source to feed the UI.
    `status` = whether the live path is reachable/configured right now.
    A source can be implemented but dormant (wired=False) — the audit
    surfaced several of those; statuses below reflect verified reality
    as of the 2026-05 data-layer pass, not aspiration.
    """
    return {
        "checked_at": datetime.utcnow().isoformat(),
        "sources": [
            {
                "key": "airroi",
                "name": "AirROI",
                "description": "Primary STR benchmark — ADR · occupancy · RevPAR. Wired into /api/market/zones/{slug}/monthly-series as the live 12-mo anchor over the seed series.",
                "status": "live" if (os.environ.get("AIRROI_API_KEY") or os.environ.get("AIRROI_BEARER")) else "not_configured (seed series fallback)",
                "wired": True,
                "cost": "pay-as-you-go · $0.01/call · ~$10/mo",
                "endpoint": "api.airroi.com/v1 · X-API-KEY via AIRROI_API_KEY",
            },
            {
                "key": "airbnb",
                "name": "Airbnb listings (Apify scrape)",
                "description": "Per-listing comps (lat/lng/price/rating), 25 per zone, 24h cache. Merged with seed comps and feeds both the comp map and the spread analyser.",
                "status": "live" if os.environ.get("APIFY_TOKEN") else "seed_fallback",
                "wired": True,
                "cost": "$0.50 per 1k results · ~$2.60/mo (cache-limited)",
                "endpoint": "api.apify.com/v2 · actor tri_angle/new-fast-airbnb-scraper · APIFY_TOKEN",
            },
            {
                "key": "datagouv",
                "name": "ADEME DPE (data.gouv / data-fair)",
                "description": "Per-commune DPE A→G distribution + F/G ban exposure. Wired into /api/market/zones/{slug}/dpe. Verified live 2026-05 (dataset meg-83tjwtg8dyz4vv7h1dqe).",
                "status": "live",
                "wired": True,
                "cost": "free (public)",
                "endpoint": "data.ademe.fr/data-fair/api/v1",
            },
            {
                "key": "eurostat",
                "name": "Eurostat",
                "description": "France tourism-nights + house-price-index. Wired into /api/market/eurostat-context. Verified live 2026-05.",
                "status": "live",
                "wired": True,
                "cost": "free (public)",
                "endpoint": "ec.europa.eu/eurostat",
            },
            {
                "key": "newsdata",
                "name": "NewsData.io",
                "description": "Live French headlines merged into /api/signals/feed, tagged UNSOURCED so the analytical layer never over-claims. Seed-only when no key.",
                "status": "live" if settings.newsdata_api_key else "seed_fallback (wired, awaiting key)",
                "wired": True,
                "cost": "free 200 req/day",
                "endpoint": "newsdata.io",
            },
            {
                "key": "osm",
                "name": "OpenStreetMap / Nominatim",
                "description": "Geocoding for scraped listings. Verified live 2026-05. Used by the Apify scrape path, not a standalone route.",
                "status": "live",
                "wired": True,
                "cost": "free (1 req/s)",
                "endpoint": "nominatim.openstreetmap.org",
            },
            {
                "key": "dvf",
                "name": "DVF (Demandes de Valeurs Foncières)",
                "description": "Transaction prices. NO live query API — DVF ships only as yearly zipped CSV on data.gouv.fr. Previous client pointed at a dead endpoint; left dormant pending a CSV-ingest job.",
                "status": "seed_fallback (no live query API)",
                "wired": False,
                "cost": "free (bulk CSV only)",
                "endpoint": "data.gouv.fr/datasets/demandes-de-valeurs-foncieres (CSV)",
            },
            {
                "key": "insee",
                "name": "INSEE Melodi",
                "description": "Vacancy + population. Melodi anonymous observation paths 404 as of 2026-05; commune vacancy/population served from the INSEE-2021-based seed instead.",
                "status": "seed_fallback (Melodi anon endpoint unreachable)",
                "wired": False,
                "cost": "free (keyless tier, currently broken)",
                "endpoint": "api.insee.fr/melodi",
            },
            {
                "key": "bdf",
                "name": "Banque de France WebStat",
                "description": "Mortgage / EURIBOR / CPI. New WebStat API gates everything behind a key (anon catalog exposes 1 dataset). Documented Q1-2026 fallback constants until BDF_API_KEY is set.",
                "status": "live" if settings.bdf_api_key else "seed_fallback (key required)",
                "wired": False,
                "cost": "free (key required since 2024 migration)",
                "endpoint": "webstat.banque-france.fr/api/explore/v2.1",
            },
            {
                "key": "meteofrance",
                "name": "Météo-France",
                "description": "Climatological normals for ski-zone occupancy. Public API requires registration token; dormant until METEOFRANCE_API_KEY is set.",
                "status": "live" if os.environ.get("METEOFRANCE_API_KEY") else "not_configured",
                "wired": False,
                "cost": "free (registration token)",
                "endpoint": "portail-api.meteofrance.fr",
            },
            {
                "key": "seloger",
                "name": "SeLoger + LeBonCoin (scrape)",
                "description": "Long-term rental asking prices. Scraper is a stub (selectors not wired); rental comps served from the expanded seed corpus.",
                "status": "seed_fallback (scraper stub)",
                "wired": False,
                "cost": "scrape (best-effort)",
                "endpoint": "seloger.com · leboncoin.fr",
            },
            {
                "key": "airdna",
                "name": "AirDNA Enterprise (optional)",
                "description": "Paid fallback for zones AirROI misses (Pays de Gex, Geneva periphery). Not needed while seed series covers those zones.",
                "status": "live" if os.environ.get("AIRDNA_BEARER") else "not_configured",
                "wired": False,
                "cost": "paid · ~30× AirROI · enable only if AirROI gap blocks",
                "endpoint": "api.airdna.co/api/enterprise/v2 · AIRDNA_BEARER",
            },
            {
                "key": "regulation",
                "name": "Regulation register",
                "description": "Meublé touristique flags + DPE min-class + 120-day cap per commune. Curated seed (regulations.json), surfaced via /api/signals/regulation.",
                "status": "seed (curated)",
                "wired": True,
                "cost": "free (curated)",
                "endpoint": "data.gouv.fr · mairie websites",
            },
            {
                "key": "anthropic",
                "name": "Claude API",
                "description": "Narrative briefing language polish. Deterministic draft is the always-on backstop.",
                "status": "live" if settings.anthropic_api_key else "deterministic_only",
                "wired": True,
                "cost": "metered, €50/mo cap",
                "endpoint": "api.anthropic.com",
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

"""
Data-source status route — surfaces which feeds are live vs falling
back to seeds. Powers the data-provenance ribbon in the sidebar.
"""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter

from config import settings


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
                "name": "Banque de France",
                "description": "Mortgage rates, EURIBOR, consumer credit",
                "status": "live",
                "cost": "free (public)",
                "endpoint": "webstat.banque-france.fr",
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
                "name": "Airbnb (scrape)",
                "description": "ADR + occupancy proxies for comp listings",
                "status": "seed_fallback",
                "cost": "scrape (best-effort)",
                "endpoint": "airbnb.fr search results",
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
                "key": "airdna",
                "name": "AirDNA",
                "description": "Proprietary ADR/RevPAR benchmarks",
                "status": "live" if os.environ.get("AIRDNA_BEARER") else "not_configured",
                "cost": "~€68/month",
                "endpoint": "api.airdna.co",
            },
            {
                "key": "airroi",
                "name": "AirROI",
                "description": "Peer-recommended ADR + occupancy benchmarks",
                "status": "live" if os.environ.get("AIRROI_BEARER") else "not_configured",
                "cost": "freemium",
                "endpoint": "airroi.com",
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
        ],
    }

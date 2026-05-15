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
                "name": "Airbnb comps (curated seed)",
                "description": "Per-commune comps from the curated seed corpus. The Apify live scrape was REMOVED 2026-05: the actor ignored the per-call item cap and Render's cache is ephemeral, so every request re-scraped whole cities (~$50 in one session). Seed-only by design; zero per-call cost.",
                "status": "seed (Apify removed)",
                "wired": True,
                "cost": "free (curated)",
                "endpoint": "backend/data/seeds/airbnb_comps.json",
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
                "key": "carte_loyers",
                "name": "Carte des loyers (official rent €/m²)",
                "description": "Per-commune predicted asking rent €/m² with 95% interval, from the DHUP/ANIL ministry model on data.gouv.fr. Wired into /rent-benchmark and the rent side of /spread. Replaces the SeLoger/LeBonCoin scrape, which is impossible server-side (both DataDome-walled, verified 2026-05). Live-refreshed per process; committed 2025 official seed as fallback.",
                "status": "live (data.gouv Carte des loyers 2025)",
                "wired": True,
                "cost": "free (official CSV, no key, no per-call billing)",
                "endpoint": "data.gouv.fr · carte-des-loyers · DHUP/ANIL",
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

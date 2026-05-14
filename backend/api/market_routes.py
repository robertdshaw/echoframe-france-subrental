"""Comp listings + market-overview routes."""

from __future__ import annotations

import statistics
from typing import List

from fastapi import APIRouter, Query

from api.schemas import CompListing
from data.property_seeder import load_airbnb_comps, load_rental_comps

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/zones/{slug}/airbnb-comps", response_model=List[CompListing])
async def airbnb_comps(slug: str) -> List[CompListing]:
    return [CompListing(**c) for c in load_airbnb_comps(slug)]


@router.get("/zones/{slug}/rental-comps", response_model=List[CompListing])
async def rental_comps(slug: str) -> List[CompListing]:
    return [CompListing(**c) for c in load_rental_comps(slug)]


@router.get("/zones/{slug}/spread")
async def airbnb_landlord_spread(slug: str):
    """Compute the per-commune Airbnb-revenue minus landlord-rent spread."""
    ab = load_airbnb_comps(slug)
    rc = load_rental_comps(slug)
    by_commune: dict[str, dict] = {}
    for c in ab:
        com = c["commune"]
        by_commune.setdefault(com, {"airbnb": [], "rental": []})["airbnb"].append(c)
    for r in rc:
        com = r["commune"]
        by_commune.setdefault(com, {"airbnb": [], "rental": []})["rental"].append(r)
    rows = []
    for com, buckets in by_commune.items():
        if not buckets["airbnb"] or not buckets["rental"]:
            continue
        med_adr = statistics.median([x["adr_eur"] for x in buckets["airbnb"]])
        med_occ = statistics.median([x["occupancy_pct"] for x in buckets["airbnb"]])
        airbnb_annual = med_adr * 365 * (med_occ / 100)
        med_rent = statistics.median([x["rent_monthly"] for x in buckets["rental"]])
        rental_annual = med_rent * 12
        rows.append({
            "commune": com,
            "airbnb_annual_eur": round(airbnb_annual, 0),
            "rental_annual_eur": round(rental_annual, 0),
            "spread_eur": round(airbnb_annual - rental_annual, 0),
            "spread_multiple": round(airbnb_annual / rental_annual, 2) if rental_annual else None,
            "n_airbnb_comps": len(buckets["airbnb"]),
            "n_rental_comps": len(buckets["rental"]),
        })
    rows.sort(key=lambda r: r["spread_eur"], reverse=True)
    return {"zone_slug": slug, "by_commune": rows}


@router.get("/overview")
async def market_overview():
    """Cross-zone summary for the market-research landing page."""
    from data.property_seeder import load_zones
    return {
        "zones": load_zones(),
        "data_sources": [
            {"name": "AirROI", "cost_eur_monthly": 10, "note": "Primary · pay-as-you-go $0.01/call · 5/7 zones covered"},
            {"name": "AirDNA Enterprise", "cost_eur_monthly": 300, "note": "Optional fallback for Pays de Gex / Geneva periphery only"},
            {"name": "Airbtics", "cost_eur_monthly": 0, "note": "Smart zones, figures differ from AirDNA"},
            {"name": "Beyond Pricing", "cost_eur_monthly": 0, "note": "Free market analysis tier"},
        ],
    }

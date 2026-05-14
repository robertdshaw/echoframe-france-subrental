"""News + regulation signal feed."""

from typing import List

from fastapi import APIRouter, Query

from api.schemas import SignalResponse
from data.property_seeder import load_news_signals, load_regulations

router = APIRouter(prefix="/api/signals", tags=["signals"])


# Map signal category → which dashboard section it influences. The
# frontend renders this as a provenance chip on each signal card.
_SECTION_FOR_CATEGORY = {
    "regulation": "§02 When to act · regulatory friction trigger",
    "rental_market": "§03 What you'll earn · landlord-side cost stack",
    "tourism": "§01 Where to source · demand-side support",
    "business": "§01 Where to source · employer density",
    "macro": "§02 When to act · mortgage-cost trigger",
    "infrastructure": "§01 Where to source · connectivity premium",
    "supply": "§02 When to act · Airbnb saturation index",
}


def _confidence_for(impact: float) -> str:
    if impact >= 0.70: return "HIGH"
    if impact >= 0.50: return "MODERATE"
    if impact >= 0.30: return "LOW"
    return "UNSOURCED"


@router.get("/feed", response_model=List[SignalResponse])
async def feed(
    zone: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    rows = load_news_signals(zone)
    rows.sort(key=lambda r: r["impact_score"], reverse=True)
    out = []
    for r in rows[:limit]:
        out.append(SignalResponse(
            id=r["id"],
            headline=r["headline"],
            source=r["source"],
            date=r["date"],
            impact_score=r["impact_score"],
            zone_relevance=r["zone_relevance"],
            category=r["category"],
            keywords=r.get("keywords", []),
            section_influence=_SECTION_FOR_CATEGORY.get(r["category"]),
            confidence=_confidence_for(r["impact_score"]),
        ))
    return out


@router.get("/regulation")
async def regulation_tracker():
    """Per-commune regulatory status: DPE, changement d'usage, 120-day, encadrement."""
    regs = load_regulations()
    return {
        "by_commune": regs.get("by_commune", {}),
        "national_2026": regs.get("national_2026", {}),
    }

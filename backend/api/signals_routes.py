"""News + regulation signal feed."""

from typing import List

from fastapi import APIRouter, Query

from api.schemas import SignalResponse
from data.newsdata_client import newsdata_client
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


_ZONE_KEYWORDS = {
    "pays-de-gex": ["gex", "ferney", "cessy", "cern", "divonne", "saint-genis"],
    "annecy-haute-savoie": ["annecy", "talloires", "sévrier", "haute-savoie"],
    "greater-lyon": ["lyon", "villeurbanne", "rhône", "caluire", "bron"],
    "grenoble-isere": ["grenoble", "isère", "meylan", "échirolles"],
    "dijon-cote-dor": ["dijon", "beaune", "côte-d'or", "bourgogne", "nuits-saint-georges"],
    "ski-access": ["megève", "morzine", "clusaz", "ski", "neige", "alpes", "les gets"],
    "geneva-periphery": ["annemasse", "thonon", "évian", "léman", "genève", "bons-en-chablais"],
}


def _infer_zones(text: str) -> List[str]:
    """Best-effort zone tagging for unscored live headlines."""
    low = (text or "").lower()
    return [z for z, kws in _ZONE_KEYWORDS.items() if any(k in low for k in kws)]


@router.get("/feed", response_model=List[SignalResponse])
async def feed(
    zone: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    include_live: bool = Query(True),
):
    """Curated seed signals (analytically scored) merged with live
    NewsData.io headlines when a key is configured.

    Live items are deliberately tagged LOW/UNSOURCED confidence and
    impact 0.40 — they are unscored by the analytical layer, so we never
    present them with fabricated certainty (global anti-hallucination
    rule). Seed items keep their curated impact_score. The client no-ops
    to seed-only when NEWSDATA_API_KEY is absent.
    """
    rows = load_news_signals(zone)
    out: List[SignalResponse] = []
    for r in rows:
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

    if include_live and newsdata_client.is_configured:
        try:
            live = await newsdata_client.get_french_news(limit=20)
            for item in live:
                if not item.get("headline"):
                    continue
                inferred = _infer_zones(
                    f"{item.get('headline','')} {' '.join(item.get('keywords') or [])}"
                )
                if zone and zone not in inferred:
                    continue
                out.append(SignalResponse(
                    id=f"live_{item.get('id') or item.get('headline')[:24]}",
                    headline=item["headline"],
                    source=item.get("source") or "NewsData.io",
                    date=item.get("date") or "",
                    impact_score=0.40,
                    zone_relevance=inferred,
                    category=item.get("category") or "other",
                    keywords=item.get("keywords") or [],
                    section_influence=_SECTION_FOR_CATEGORY.get(item.get("category") or ""),
                    confidence="UNSOURCED",
                ))
        except Exception:
            pass  # live failure never breaks the seed feed

    out.sort(key=lambda s: s.impact_score, reverse=True)
    return out[:limit]


@router.get("/regulation")
async def regulation_tracker():
    """Per-commune regulatory status: DPE, changement d'usage, 120-day, encadrement."""
    regs = load_regulations()
    return {
        "by_commune": regs.get("by_commune", {}),
        "national_2026": regs.get("national_2026", {}),
    }

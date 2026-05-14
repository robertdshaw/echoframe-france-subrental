"""LLM briefing route — deterministic draft + optional Claude polish."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.schemas import NarrativeResponse
from config import settings
from data.property_seeder import load_zones
from services.forecast_service import forecast_service


router = APIRouter(prefix="/api/narrative", tags=["narrative"])


@router.get("/{slug}", response_model=NarrativeResponse)
async def narrative(slug: str) -> NarrativeResponse:
    zones = {z["slug"]: z for z in load_zones()}
    zone = zones.get(slug)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{slug}' not found")
    forecast = await forecast_service.get_zone_forecast(slug)
    if not forecast:
        raise HTTPException(status_code=503, detail="Forecast unavailable")

    # Stage 1: deterministic draft, all numbers filled in Python.
    h12 = next((h for h in forecast.horizons if h.horizon_months == 12), forecast.horizons[0])
    verdict_phrase = {
        "TARGET": "is a high-conviction target zone",
        "WAIT":   "is a wait-and-watch zone — fundamentals OK but margin compresses",
        "AVOID":  "is currently an avoid",
    }.get(forecast.verdict, "shows mixed signals")

    paragraphs = []
    paragraphs.append(
        f"**The Call.** {forecast.zone_name} {verdict_phrase}. The 12-month "
        f"net-margin posterior is {h12.median_change_pct:+.1f}% of gross revenue, "
        f"with an 80% band of {h12.ci_80_lower:+.1f}% to {h12.ci_80_upper:+.1f}% "
        f"and a {h12.p_positive:.0%} probability of running at positive margin."
    )
    paragraphs.append(
        f"**Where to source.** Median Airbnb ADR is €{forecast.median_adr_eur:.0f}/night at "
        f"{forecast.median_occupancy_pct:.0f}% occupancy; landlord-side rent runs "
        f"€{forecast.median_rent_eur:.0f}/month across the seed comps."
    )
    paragraphs.append(
        f"**What you'll earn.** Annualised at zone medians, gross revenue lands at "
        f"€{forecast.median_adr_eur * 365 * (forecast.median_occupancy_pct/100):,.0f} "
        f"before costs. The full French cost stack (platform + cleaning + insurance + "
        f"CFE + rent + tax) nets to €{forecast.expected_net_margin_eur:,.0f}/year "
        f"({forecast.expected_net_margin_pct:.1f}% of gross)."
    )
    paragraphs.append(
        f"**Versus alternatives.** Compares against Livret A at ~3.0% (regulated "
        f"savings), an SCPI rendement at ~5.0%, and a direct long-term rental yield "
        f"on the same parcel at ~5-6%. The sub-let edge is the multiple over "
        f"direct rental, not absolute return."
    )
    paragraphs.append(
        f"**Confidence statement.** This briefing reads from a partial-pooling "
        f"forecast trained on seed comp data; live AirDNA / AirROI integration "
        f"will tighten the bands materially. Treat the 80% range as a sensible "
        f"planning envelope, not a precise prediction."
    )

    draft = "\n\n".join(paragraphs)

    # Stage 2: LLM polish — gated by API key + cost ledger. For now we
    # ship the deterministic draft directly. Wiring Claude in is a
    # one-method change once the cost ledger lands.
    if not settings.anthropic_api_key:
        return NarrativeResponse(
            status="ok",
            narrative=draft,
            model="deterministic-draft",
            generated_at=datetime.utcnow().isoformat(),
            reason="No ANTHROPIC_API_KEY configured; served deterministic draft.",
        )

    # TODO: Claude Sonnet polish (mirror Argentina narrative_service).
    return NarrativeResponse(
        status="ok",
        narrative=draft,
        model="deterministic-draft",
        generated_at=datetime.utcnow().isoformat(),
        reason="LLM polish pending wire-up; deterministic draft served.",
    )

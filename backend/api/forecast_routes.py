"""Zone-level forecasts + interactive margin calculator."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query

from api.schemas import (
    CommuneSummary,
    ConfidenceInterval,
    HorizonForecast,
    MarginRequest,
    MarginResponse,
    WaterfallLineSchema,
    ZoneForecastResponse,
    ZoneSummary,
)
from data.property_seeder import load_communes, load_zones
from services.forecast_service import forecast_service
from services.margin_calculator import MarginInputs, compute_margin

router = APIRouter(prefix="/api", tags=["forecast"])


@router.get("/zones", response_model=List[ZoneSummary])
async def list_zones() -> List[ZoneSummary]:
    """All 7 target zones with embedded net-margin verdict."""
    raw = load_zones()
    forecasts = await forecast_service.get_all_zone_forecasts()
    by_slug = {f.zone_slug: f for f in forecasts}
    out: List[ZoneSummary] = []
    for z in raw:
        f = by_slug.get(z["slug"])
        out.append(ZoneSummary(
            slug=z["slug"],
            name=z["name"],
            profile=z["profile"],
            communes=z["communes"],
            center=z["center"],
            radius_km=z["radius_km"],
            median_adr_eur=z["median_adr_eur"],
            median_rent_per_m2_eur=z["median_rent_per_m2_eur"],
            median_occupancy_pct=z["median_occupancy_pct"],
            regulatory_friction=z["regulatory_friction"],
            expected_net_margin_eur=f.expected_net_margin_eur if f else None,
            expected_net_margin_pct=f.expected_net_margin_pct if f else None,
            verdict=f.verdict if f else None,
        ))
    return out


@router.get("/zones/{slug}/forecast", response_model=ZoneForecastResponse)
async def zone_forecast(slug: str) -> ZoneForecastResponse:
    f = await forecast_service.get_zone_forecast(slug)
    if not f:
        raise HTTPException(status_code=404, detail=f"Zone '{slug}' not found")
    zones = {z["slug"]: z for z in load_zones()}
    z = zones[slug]
    return ZoneForecastResponse(
        zone=ZoneSummary(
            slug=z["slug"], name=z["name"], profile=z["profile"], communes=z["communes"],
            center=z["center"], radius_km=z["radius_km"],
            median_adr_eur=z["median_adr_eur"], median_rent_per_m2_eur=z["median_rent_per_m2_eur"],
            median_occupancy_pct=z["median_occupancy_pct"], regulatory_friction=z["regulatory_friction"],
            expected_net_margin_eur=f.expected_net_margin_eur,
            expected_net_margin_pct=f.expected_net_margin_pct, verdict=f.verdict,
        ),
        forecasts=[
            HorizonForecast(
                horizon_months=h.horizon_months,
                median_change_pct=h.median_change_pct,
                ci_80=ConfidenceInterval(lower=h.ci_80_lower, upper=h.ci_80_upper, confidence_level=80),
                ci_95=ConfidenceInterval(lower=h.ci_95_lower, upper=h.ci_95_upper, confidence_level=95),
                p_positive=h.p_positive,
            )
            for h in f.horizons
        ],
        current_regime=f.current_regime,
        regime_confidence=f.regime_confidence,
        timestamp=f.timestamp,
    )


@router.get("/communes", response_model=List[CommuneSummary])
async def list_communes(zone: str | None = Query(None)) -> List[CommuneSummary]:
    rows = load_communes()
    if zone:
        rows = [r for r in rows if r.get("zone_slug") == zone]
    return [CommuneSummary(**r) for r in rows]


@router.post("/margin", response_model=MarginResponse)
async def calc_margin(req: MarginRequest) -> MarginResponse:
    """Live, interactive margin computation. Called as the user drags sliders."""
    result = compute_margin(MarginInputs(
        adr_eur=req.adr_eur,
        occupancy_pct=req.occupancy_pct,
        rent_monthly_eur=req.rent_monthly_eur,
        capacity=req.capacity,
        charges_monthly_eur=req.charges_monthly_eur,
        platform_commission_pct=req.platform_commission_pct,
        tax_regime=req.tax_regime,
        classification=req.classification,
        tmi_pct=req.tmi_pct,
    ))
    return MarginResponse(
        gross_revenue_annual_eur=result.gross_revenue_annual_eur,
        net_revenue_annual_eur=result.net_revenue_annual_eur,
        landlord_costs_annual_eur=result.landlord_costs_annual_eur,
        operating_costs_annual_eur=result.operating_costs_annual_eur,
        taxable_base_eur=result.taxable_base_eur,
        tax_eur=result.tax_eur,
        net_margin_annual_eur=result.net_margin_annual_eur,
        net_margin_pct_of_revenue=result.net_margin_pct_of_revenue,
        waterfall=[WaterfallLineSchema(**w.__dict__) for w in result.waterfall],
        regime_used=result.regime_used,
        notes=result.notes,
    )

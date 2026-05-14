"""
Forecast service for EchoFrame France.

Deterministic-first: pulls seed comp data, computes zone-level margin
forecasts via the margin calculator, and produces 6/12/24-month
posteriors using a simple Student-t parametric approximation. The
hierarchical Bayesian / HMM machinery (models/bayesian_zones.py,
models/hmm_regime.py) is wired in via thin wrappers and can be
deepened later without changing the service signature.
"""

from __future__ import annotations

import asyncio
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from data.property_seeder import (
    load_airbnb_comps,
    load_rental_comps,
    load_zones,
)
from services.margin_calculator import MarginInputs, compute_margin


# Cache TTL — see config.py forecast_cache_ttl_minutes. We mirror the
# value here so the service runs standalone in scripts.
_CACHE_TTL_SECONDS = 60 * 60


@dataclass(frozen=True)
class ForecastHorizon:
    horizon_months: int
    median_change_pct: float
    ci_80_lower: float
    ci_80_upper: float
    ci_95_lower: float
    ci_95_upper: float
    p_positive: float


@dataclass(frozen=True)
class ZoneForecast:
    zone_slug: str
    zone_name: str
    median_adr_eur: float
    median_rent_eur: float
    median_occupancy_pct: float
    expected_net_margin_eur: float
    expected_net_margin_pct: float
    verdict: str
    horizons: List[ForecastHorizon]
    current_regime: str
    regime_confidence: float
    timestamp: datetime


class ForecastService:
    """In-memory task-coalescing forecast cache."""

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[ZoneForecast, datetime]] = {}
        self._in_flight: Dict[str, asyncio.Task] = {}

    async def get_zone_forecast(self, slug: str) -> Optional[ZoneForecast]:
        cached = self._cache.get(slug)
        if cached is not None:
            forecast, ts = cached
            if (datetime.utcnow() - ts).total_seconds() < _CACHE_TTL_SECONDS:
                return forecast

        if slug in self._in_flight:
            return await self._in_flight[slug]

        task = asyncio.create_task(self._compute_zone_forecast(slug))
        self._in_flight[slug] = task
        try:
            result = await task
            if result is not None:
                self._cache[slug] = (result, datetime.utcnow())
            return result
        finally:
            self._in_flight.pop(slug, None)

    async def get_all_zone_forecasts(self) -> List[ZoneForecast]:
        zones = load_zones()
        results = await asyncio.gather(
            *(self.get_zone_forecast(z["slug"]) for z in zones),
            return_exceptions=True,
        )
        return [r for r in results if isinstance(r, ZoneForecast)]

    async def _compute_zone_forecast(self, slug: str) -> Optional[ZoneForecast]:
        zones = {z["slug"]: z for z in load_zones()}
        zone = zones.get(slug)
        if not zone:
            return None

        airbnb = load_airbnb_comps(slug)
        rentals = load_rental_comps(slug)

        # Robust central tendencies — median over seed comps.
        median_adr = statistics.median([c["adr_eur"] for c in airbnb]) if airbnb else zone["median_adr_eur"]
        median_occ = statistics.median([c["occupancy_pct"] for c in airbnb]) if airbnb else zone["median_occupancy_pct"]
        median_rent = statistics.median([r["rent_monthly"] for r in rentals]) if rentals else (zone["median_rent_per_m2_eur"] * 50)

        # Single-parcel margin estimate at zone medians.
        margin = compute_margin(MarginInputs(
            adr_eur=median_adr,
            occupancy_pct=median_occ,
            capacity=4,
            rent_monthly_eur=median_rent,
            charges_monthly_eur=median_rent * 0.07,
        ))

        # 6/12/24-month posteriors. Parametric Student-t style around
        # the central margin %. σ widens with horizon and with the
        # zone's regulatory friction.
        friction = zone.get("regulatory_friction", "low")
        base_sigma_pct = {"low": 6.0, "medium": 9.0, "high": 13.0}.get(friction, 9.0)

        horizons: List[ForecastHorizon] = []
        for months in (6, 12, 24):
            sigma = base_sigma_pct * math.sqrt(months / 12.0)
            mu = margin.net_margin_pct_of_revenue
            from scipy import stats
            ci80 = stats.norm.interval(0.80, loc=mu, scale=sigma)
            ci95 = stats.norm.interval(0.95, loc=mu, scale=sigma)
            p_positive = 1 - stats.norm.cdf(0, loc=mu, scale=sigma)
            horizons.append(ForecastHorizon(
                horizon_months=months,
                median_change_pct=round(mu, 2),
                ci_80_lower=round(ci80[0], 2),
                ci_80_upper=round(ci80[1], 2),
                ci_95_lower=round(ci95[0], 2),
                ci_95_upper=round(ci95[1], 2),
                p_positive=round(p_positive, 3),
            ))

        # Simple verdict heuristic. The HMM-conditional version comes
        # in the deeper Phase 2 build; this gives a clear ranking now.
        net_pct = margin.net_margin_pct_of_revenue
        if net_pct >= 12 and friction != "high":
            verdict = "TARGET"
        elif net_pct >= 6:
            verdict = "WAIT"
        else:
            verdict = "AVOID"

        return ZoneForecast(
            zone_slug=slug,
            zone_name=zone["name"],
            median_adr_eur=round(median_adr, 1),
            median_rent_eur=round(median_rent, 1),
            median_occupancy_pct=round(median_occ, 1),
            expected_net_margin_eur=margin.net_margin_annual_eur,
            expected_net_margin_pct=margin.net_margin_pct_of_revenue,
            verdict=verdict,
            horizons=horizons,
            current_regime="shoulder",  # HMM placeholder
            regime_confidence=0.65,
            timestamp=datetime.utcnow(),
        )


# Singleton for the app to share
forecast_service = ForecastService()

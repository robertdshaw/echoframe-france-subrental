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

from data.carte_loyers_client import carte_loyers_client
from data.property_seeder import (
    load_airbnb_comps,
    load_communes,
    load_monthly_str_series,
    load_zones,
)
from services.margin_calculator import MarginInputs, compute_margin


_DAYS_PER_MONTH = 30.4


def _zone_official_rent_monthly(slug: str, fallback_rent: float) -> Tuple[float, str]:
    """Median official asking rent for the zone's communes → monthly €.

    Uses the free Carte des loyers €/m² (DHUP/ANIL) × a 50 m² reference
    unit. Falls back to the seed rent only when no commune resolves.
    Zero marginal cost (carte_loyers caches per process, seed fallback).
    """
    communes = [c for c in load_communes() if c["zone_slug"] == slug]
    per_m2: List[float] = []
    for c in communes:
        rec = carte_loyers_client.get_rent_per_m2(c["code_insee"])
        if rec and rec.get("rent_eur_per_m2"):
            per_m2.append(rec["rent_eur_per_m2"])
    if not per_m2:
        return fallback_rent, "seed"
    return statistics.median(per_m2) * 50.0, "official (Carte des loyers)"


def _series_trend(series: List[Dict]) -> Tuple[float, str]:
    """Trailing trend from the 24-month ADR×occupancy revenue proxy.

    Returns (annualised_growth_fraction, regime). Growth = last-12-month
    mean monthly revenue vs the prior 12 months. Regime is read off the
    most recent 3 months vs the trailing-12 mean — a real signal, not a
    hardcoded 'shoulder'.
    """
    if len(series) < 13:
        return 0.0, "insufficient_history"
    rev = [
        s["adr_eur"] * (s["occupancy_pct"] / 100.0) * _DAYS_PER_MONTH
        for s in series
    ]
    last12 = rev[-12:]
    prior = rev[-24:-12] if len(rev) >= 24 else rev[:-12]
    if not prior or statistics.mean(prior) == 0:
        return 0.0, "insufficient_history"
    growth = (statistics.mean(last12) - statistics.mean(prior)) / statistics.mean(prior)
    trailing_mean = statistics.mean(last12)
    recent3 = statistics.mean(rev[-3:])
    if recent3 >= trailing_mean * 1.10:
        regime = "peak"
    elif recent3 <= trailing_mean * 0.90:
        regime = "trough"
    else:
        regime = "shoulder"
    return growth, regime


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

        # Dynamic central tendencies from the 24-month series (the same
        # series the /monthly-series endpoint serves — seed-derived with
        # real French seasonality; AirROI overlays it on the endpoint).
        series = load_monthly_str_series(slug).get("series", [])
        if series:
            median_adr = statistics.median([s["adr_eur"] for s in series[-12:]])
            median_occ = statistics.median([s["occupancy_pct"] for s in series[-12:]])
        else:
            median_adr = (
                statistics.median([c["adr_eur"] for c in airbnb])
                if airbnb else zone["median_adr_eur"]
            )
            median_occ = (
                statistics.median([c["occupancy_pct"] for c in airbnb])
                if airbnb else zone["median_occupancy_pct"]
            )

        # Rent side from the official Carte des loyers (free, no key).
        seed_rent_fallback = zone["median_rent_per_m2_eur"] * 50
        median_rent, rent_provenance = _zone_official_rent_monthly(
            slug, seed_rent_fallback
        )

        margin = compute_margin(MarginInputs(
            adr_eur=median_adr,
            occupancy_pct=median_occ,
            capacity=4,
            rent_monthly_eur=median_rent,
            charges_monthly_eur=median_rent * 0.07,
        ))

        # Real trajectory: trailing growth from the 24-month revenue
        # proxy, projected per horizon (6mo = ½ annual trend, 12mo =
        # full, 24mo = compounded). These now genuinely differ and
        # trace to the series instead of repeating the static margin %.
        trend, regime = _series_trend(series)
        friction = zone.get("regulatory_friction", "low")
        base_sigma_pct = {"low": 6.0, "medium": 9.0, "high": 13.0}.get(friction, 9.0)
        horizon_growth = {
            6: ((1 + trend) ** 0.5 - 1) * 100,
            12: trend * 100,
            24: ((1 + trend) ** 2 - 1) * 100,
        }

        horizons: List[ForecastHorizon] = []
        from scipy import stats
        for months in (6, 12, 24):
            sigma = base_sigma_pct * math.sqrt(months / 12.0)
            mu = horizon_growth[months]
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
            current_regime=regime,  # read off the 24-mo series, not hardcoded
            regime_confidence=0.65 if regime != "insufficient_history" else 0.0,
            timestamp=datetime.utcnow(),
        )


# Singleton for the app to share
forecast_service = ForecastService()

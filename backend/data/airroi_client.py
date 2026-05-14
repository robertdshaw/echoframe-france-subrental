"""
AirROI Airbnb Data API client — market-level benchmarks for our zones.

Docs: https://www.airroi.com/api/documentation
Pricing: pay-as-you-go, $0.01/call, $10 minimum top-up. Self-serve key at
https://www.airroi.com/api/developer/activate (set as AIRROI_API_KEY).

The AirROI API addresses markets by a {country, region, locality} tuple
rather than by a numeric id like AirDNA, so resolution is just a static
mapping. The 13 documented market-level endpoints all share the same body
shape — POST to /markets/{metric} with the market tuple, num_months, and
optionally currency / filters.

Coverage caveat for our 7 French zones:
  · 5 zones resolve cleanly: annecy, lyon, grenoble, dijon, ski-access
    (via Chamonix-Mont-Blanc as the closest covered ski market).
  · 2 zones are NOT in AirROI's tracked French cities: pays-de-gex and
    geneva-periphery. For those we return None and let the caller fall
    back to seed comps.

Documented field assumptions:
  · POST /markets/occupancy             → series with `occupancy_rate`
  · POST /markets/average-daily-rate    → series with `adr`
  · POST /markets/revpar                → series with `revpar`
  · POST /markets/revenue               → series with `revenue`
  · `currency: "native"` returns local currency (EUR for French markets).
The docs don't publish exact response field names, so the extractor below
checks a couple of common keys per metric. Once we make the first real
call we can tighten this up.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


# Zone slug → AirROI {country, region, locality}. `None` means the zone is
# not covered by AirROI and the caller should fall back to seed comps.
# Region names use AirROI's display form (with hyphens and accents) as
# shown on their French country page.
ZONE_TO_AIRROI_MARKET: Dict[str, Optional[Dict[str, str]]] = {
    "annecy-haute-savoie": {
        "country": "France",
        "region": "Auvergne-Rhône-Alpes",
        "locality": "Annecy",
    },
    "greater-lyon": {
        "country": "France",
        "region": "Auvergne-Rhône-Alpes",
        "locality": "Lyon",
    },
    "grenoble-isere": {
        "country": "France",
        "region": "Auvergne-Rhône-Alpes",
        "locality": "Grenoble",
    },
    "dijon-cote-dor": {
        "country": "France",
        "region": "Bourgogne – Franche-Comté",
        "locality": "Dijon",
    },
    # Ski-access proxy: Chamonix is the most premium of AirROI's covered
    # French ski towns. Our seed zone bundles Megève / Morzine / La Clusaz,
    # which AirROI doesn't track individually, so Chamonix sets a high
    # benchmark — caller should display it as "proxy: Chamonix-Mont-Blanc"
    # rather than implying it covers the whole zone.
    "ski-access": {
        "country": "France",
        "region": "Auvergne-Rhône-Alpes",
        "locality": "Chamonix-Mont-Blanc",
    },
    "pays-de-gex": None,
    "geneva-periphery": None,
}


class AirROIClient:
    """AirROI market-level data — operator-configurable via AIRROI_API_KEY."""

    BASE_URL = "https://api.airroi.com/v1/"
    TIMEOUT = 15.0
    CURRENCY = "native"  # → EUR for French markets

    # Path + response field per metric, derived from the documentation.
    # If the live API turns out to use slightly different keys, update the
    # value_keys list — the extractor tries each in order.
    METRICS = {
        "adr": ("markets/average-daily-rate", ["adr", "average_daily_rate", "value"]),
        "occupancy": ("markets/occupancy", ["occupancy_rate", "occupancy", "value"]),
        "revpar": ("markets/revpar", ["revpar", "value"]),
        "revenue": ("markets/revenue", ["revenue", "value"]),
    }

    def __init__(self) -> None:
        # Accept both names — older scaffolding used AIRROI_BEARER, the
        # real product uses an API key, not a bearer.
        self.api_key = os.environ.get("AIRROI_API_KEY") or os.environ.get(
            "AIRROI_BEARER"
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-KEY": self.api_key or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _extract_series(body: Any) -> List[Dict[str, Any]]:
        """Find the time-series list inside an AirROI response.

        AirROI's docs describe the result as a list of monthly buckets but
        don't lock down the wrapper. We accept the common shapes: top-level
        list, `data`, `results`, `metrics`, or nested under `payload`.
        """
        if isinstance(body, list):
            return [r for r in body if isinstance(r, dict)]
        if not isinstance(body, dict):
            return []
        for key in ("data", "results", "metrics", "series"):
            v = body.get(key)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
        payload = body.get("payload")
        if isinstance(payload, dict):
            return AirROIClient._extract_series(payload)
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        return []

    @staticmethod
    def _trailing_avg(
        series: List[Dict[str, Any]],
        value_keys: List[str],
        months: int = 12,
    ) -> Optional[float]:
        """Average the last `months` values, trying each candidate field name."""
        vals: List[float] = []
        for row in series[-months:]:
            v: Any = None
            for key in value_keys:
                if key in row and isinstance(row[key], (int, float)):
                    v = row[key]
                    break
            if isinstance(v, (int, float)):
                vals.append(float(v))
        if not vals:
            return None
        return sum(vals) / len(vals)

    async def _fetch_metric(
        self,
        market: Dict[str, str],
        metric: str,
        months: int = 24,
    ) -> Optional[List[Dict[str, Any]]]:
        """POST /markets/{metric} → time-series list."""
        path, _ = self.METRICS[metric]
        body = {
            "market": market,
            "num_months": months,
            "currency": self.CURRENCY,
        }
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.post(
                    f"{self.BASE_URL}{path}",
                    headers=self._headers(),
                    json=body,
                )
                r.raise_for_status()
                return self._extract_series(r.json())
        except Exception as exc:
            logger.warning(
                "AirROI %s for %s/%s failed: %s",
                metric,
                market.get("locality"),
                market.get("region"),
                exc,
            )
            return None

    async def get_zone_benchmarks(
        self,
        zone_slug: str,
    ) -> Optional[Dict[str, Any]]:
        """Trailing-12-month ADR / occupancy / RevPAR / monthly revenue.

        Returns None when the zone isn't mapped (Pays de Gex, Geneva
        periphery) OR when AirROI isn't configured. None means "show seed
        fallback" to the UI.
        """
        if not self.is_configured:
            return None
        market = ZONE_TO_AIRROI_MARKET.get(zone_slug)
        if market is None:
            return None

        adr, occ, revpar, revenue = await asyncio.gather(
            self._fetch_metric(market, "adr"),
            self._fetch_metric(market, "occupancy"),
            self._fetch_metric(market, "revpar"),
            self._fetch_metric(market, "revenue"),
        )

        adr_eur = self._trailing_avg(adr or [], self.METRICS["adr"][1])
        occ_pct = self._trailing_avg(occ or [], self.METRICS["occupancy"][1])
        revpar_eur = self._trailing_avg(revpar or [], self.METRICS["revpar"][1])
        revenue_eur = self._trailing_avg(revenue or [], self.METRICS["revenue"][1])

        # AirROI sometimes returns occupancy as 0–1 (decimal) rather than 0–100.
        # Normalise upward so the dashboard always speaks in percent.
        if isinstance(occ_pct, (int, float)) and occ_pct <= 1.5:
            occ_pct = occ_pct * 100

        if all(v is None for v in (adr_eur, occ_pct, revpar_eur, revenue_eur)):
            return None

        proxy_note = (
            "Chamonix-Mont-Blanc proxy (AirROI doesn't track Megève / Morzine / La Clusaz individually)"
            if zone_slug == "ski-access"
            else None
        )

        return {
            "zone_slug": zone_slug,
            "market": market,
            "adr_eur_trailing_12mo": adr_eur,
            "occupancy_pct_trailing_12mo": occ_pct,
            "revpar_eur_trailing_12mo": revpar_eur,
            "avg_monthly_revenue_eur": revenue_eur,
            "proxy_note": proxy_note,
            "source": "AirROI Airbnb Data API",
            "fetched_at": datetime.utcnow().isoformat(),
        }


airroi_client = AirROIClient()

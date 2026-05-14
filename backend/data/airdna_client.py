"""
AirDNA Enterprise API v2 client.

Spec: https://api.airdna.co/api/enterprise/v2 (OpenAPI 3.1.0).
Auth: Authorization: Bearer <token>. Set via AIRDNA_BEARER env var.

Response envelope shape — every endpoint returns:
    { "payload": <body>, "status": {type, response_id, message} }
so we always read `r.json()["payload"]` before touching field names.

Resolution flow for our French zones:
  1. POST /market/search with {"search_term": "Annecy", "pagination": {...}}
     → payload.results[i].id is the AirDNA market id, e.g. "airdna-163".
     We cache it per process.
  2. GET /market/{marketId}
     → payload.metrics = {market_score, revenue, booked, daily_rate, revpar}
       (trailing-12-month summary that AirDNA pre-computes).
  3. POST /market/{marketId}/metrics/{occupancy,adr,avg_revenue,revpar}
     → payload.metrics is a list of {date: "YYYY-MM", <value_key>: number, ...}
       plus monthly_pct_change / yearly_pct_change at top level.

Filter caveats from the spec:
  · `filters` is an array of {field, type, value} objects, not a map.
  · `listing_status` is NOT a supported filter (active listings is the
    default behaviour). Sending it returns HTTP 400.
  · `currency` is accepted by adr / avg_revenue / revpar but NOT by
    occupancy or active_listings_count — those have no currency dimension.

Status in this product: AirROI is the primary provider (see
airroi_client.py). AirDNA is kept here as an optional fallback only — it
costs ~30× more and we only need it if AirROI's coverage gap for Pays de
Gex and Geneva periphery becomes a blocker.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class AirDNAClient:
    """AirDNA Enterprise API v2 — operator-configurable via AIRDNA_BEARER."""

    AIRDNA_BASE = "https://api.airdna.co/api/enterprise/v2/"
    TIMEOUT = 15.0
    CURRENCY = "eur"

    # Field name returned by each metric endpoint, used to pull the trailing
    # average. From the swagger response schemas.
    METRIC_VALUE_KEYS = {
        "occupancy": "occupancy_rate",
        "adr": "adr",
        "avg_revenue": "revenue",
        "revpar": "revpar",
    }
    # Endpoints that accept the `currency` field (occupancy is unit-less).
    METRIC_TAKES_CURRENCY = {"adr", "avg_revenue", "revpar"}

    def __init__(self) -> None:
        self.airdna_token = os.environ.get("AIRDNA_BEARER")
        self._market_id_cache: Dict[str, Optional[str]] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.airdna_token)

    def _airdna_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.airdna_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _payload(r: httpx.Response) -> Dict[str, Any]:
        """Pull the `payload` field from AirDNA's response envelope."""
        body = r.json()
        return body.get("payload") if isinstance(body, dict) else {}

    async def resolve_market_id(self, query: str) -> Optional[str]:
        """POST /market/search → first 'market'-typed hit's id (cached).

        AirDNA search returns a mix of markets and submarkets. For zone-level
        benchmarks we want the parent market, so we skip submarkets.
        """
        if not self.airdna_token:
            return None
        if query in self._market_id_cache:
            return self._market_id_cache[query]
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.post(
                    f"{self.AIRDNA_BASE}market/search",
                    headers=self._airdna_headers(),
                    json={
                        "search_term": query,
                        "pagination": {"page_size": 5, "offset": 0},
                    },
                )
                r.raise_for_status()
                payload = self._payload(r) or {}
                results = payload.get("results") or []
                market_id: Optional[str] = None
                for hit in results:
                    if hit.get("type") == "market":
                        market_id = hit.get("id")
                        break
                if not market_id and results:
                    market_id = results[0].get("id")
                self._market_id_cache[query] = str(market_id) if market_id else None
                return self._market_id_cache[query]
        except Exception as exc:
            logger.warning("AirDNA market search for %r failed: %s", query, exc)
            self._market_id_cache[query] = None
            return None

    async def _get_market_summary(self, market_id: str) -> Optional[Dict[str, Any]]:
        """GET /market/{marketId} — trailing-12-month summary metrics."""
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.AIRDNA_BASE}market/{market_id}",
                    headers=self._airdna_headers(),
                )
                r.raise_for_status()
                return self._payload(r)
        except Exception as exc:
            logger.warning("AirDNA market summary %s failed: %s", market_id, exc)
            return None

    async def _post_metric(
        self,
        market_id: str,
        metric: str,
        months: int = 24,
    ) -> Optional[Dict[str, Any]]:
        """POST /market/{marketId}/metrics/{metric}.

        The spec says occupancy doesn't accept currency; revenue/adr/revpar do.
        Filters are sent as an empty array (we want market-wide defaults).
        """
        body: Dict[str, Any] = {"num_months": months, "filters": []}
        if metric in self.METRIC_TAKES_CURRENCY:
            body["currency"] = self.CURRENCY
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.post(
                    f"{self.AIRDNA_BASE}market/{market_id}/metrics/{metric}",
                    headers=self._airdna_headers(),
                    json=body,
                )
                r.raise_for_status()
                return self._payload(r)
        except Exception as exc:
            logger.warning("AirDNA metric %s/%s failed: %s", market_id, metric, exc)
            return None

    @staticmethod
    def _trailing_avg(
        payload: Optional[Dict[str, Any]],
        value_key: str,
        months: int = 12,
    ) -> Optional[float]:
        """Average the last `months` observations from a metric payload.

        Per the swagger, each entry in payload.metrics is keyed by `date`
        plus one of: occupancy_rate, adr, revenue, revpar.
        """
        if not payload:
            return None
        series = payload.get("metrics") or []
        vals: List[float] = []
        for row in series[-months:]:
            if not isinstance(row, dict):
                continue
            v = row.get(value_key)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        if not vals:
            return None
        return sum(vals) / len(vals)

    async def get_market_benchmarks(self, query: str) -> Optional[Dict[str, Any]]:
        """One-call zone benchmark.

        Combines:
          · GET /market/{id} — pre-computed trailing-12-month summary
            (market_score, revpar, booked, daily_rate, revenue).
          · POST /market/{id}/metrics/{adr,occupancy,revpar,avg_revenue}
            — monthly series, from which we pull our own trailing-12-month
            average (in EUR for the currency-aware metrics).

        We return both: the summary fields are fast and always-on, the
        trailing averages are useful when the operator wants to see the
        chart series later. If either fails the other still surfaces.
        """
        market_id = await self.resolve_market_id(query)
        if not market_id:
            return None

        summary, adr, occ, revpar, revenue = await asyncio.gather(
            self._get_market_summary(market_id),
            self._post_metric(market_id, "adr"),
            self._post_metric(market_id, "occupancy"),
            self._post_metric(market_id, "revpar"),
            self._post_metric(market_id, "avg_revenue"),
        )

        summary_metrics = (summary or {}).get("metrics") or {}

        return {
            "query": query,
            "market_id": market_id,
            "name": (summary or {}).get("name"),
            "market_type": (summary or {}).get("market_type"),
            # Summary endpoint values (USD by default, but operators read
            # these as relative scores; for absolute EUR figures use the
            # trailing fields below).
            "market_score": summary_metrics.get("market_score"),
            "summary_adr_usd": summary_metrics.get("daily_rate"),
            "summary_revpar_usd": summary_metrics.get("revpar"),
            "summary_occupancy_pct": (
                summary_metrics.get("booked") * 100
                if isinstance(summary_metrics.get("booked"), (int, float))
                else None
            ),
            # Trailing-12-month averages we compute ourselves, in EUR where
            # applicable. These are what the zone card should display.
            "adr_eur_trailing_12mo": self._trailing_avg(adr, "adr"),
            "occupancy_pct_trailing_12mo": self._trailing_avg(occ, "occupancy_rate"),
            "revpar_eur_trailing_12mo": self._trailing_avg(revpar, "revpar"),
            "avg_monthly_revenue_eur": self._trailing_avg(revenue, "revenue"),
            "source": "AirDNA Enterprise API v2",
            "fetched_at": datetime.utcnow().isoformat(),
        }

    # Back-compat shim — older callers expect get_zone_benchmarks(commune).
    async def get_zone_benchmarks(self, commune: str) -> Optional[Dict[str, Any]]:
        if not self.airdna_token:
            return None
        res = await self.get_market_benchmarks(commune)
        if not res:
            return None
        return {
            "commune": commune,
            "adr_eur": res.get("adr_eur_trailing_12mo")
            or res.get("summary_adr_usd"),
            "occupancy_pct": res.get("occupancy_pct_trailing_12mo")
            or res.get("summary_occupancy_pct"),
            "revpar_eur": res.get("revpar_eur_trailing_12mo")
            or res.get("summary_revpar_usd"),
            "market_score": res.get("market_score"),
            "source": res["source"],
            "fetched_at": res["fetched_at"],
        }


airdna_client = AirDNAClient()

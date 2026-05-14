"""
Banque de France WebStat client — interest rates, credit, macro.

Endpoint: https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets/
Auth: REQUIRED — register at webstat.banque-france.fr, generate a key
under "Mes clés d'API", set BDF_API_KEY env var. Free tier.

The new BdF API gates everything behind an Authorization: Apikey
<key> header. The legacy unauthenticated /ws_wsen/ endpoint has been
deprecated, so when BDF_API_KEY is absent we fall back to documented
Q1 2026 constants rather than attempting an unauthenticated call.

Key series for sub-rental underwriting:
  · MIR.M.FR.B.A2C.A.R.A.2240.EUR.N — taux moyen crédit immobilier
  · MIR.M.FR.B.A2A.AM.R.A.2240.EUR.N — taux moyen crédit conso
  · BSI.M.FR.N.A.A20.A.1.U2.2253.Z01.E — encours crédits immobilier

The new endpoint takes pseudo-SQL queries against an `observations`
table; see https://webstat.banque-france.fr/fr/pages/api-guide/ for
the full guide.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from config import settings


logger = logging.getLogger(__name__)


# Q1 2026 Banque de France market readings. Used when the live API is
# absent / unreachable. Documented sources kept inline so the dashboard
# can show provenance.
_FALLBACKS = {
    "mortgage_rate_pct": {
        "value": 3.42,
        "as_of": "2026-Q1",
        "note": "Taux moyen TAEG crédit immobilier · stable ~3.4% since 2025Q3",
        "source": "BdF MIR (fallback)",
    },
    "consumer_credit_rate_pct": {
        "value": 6.82,
        "as_of": "2026-Q1",
        "note": "Taux moyen crédit consommation",
        "source": "BdF MIR (fallback)",
    },
    "euribor_3m_pct": {
        "value": 2.85,
        "as_of": "2026-Q1",
        "note": "EURIBOR 3-month",
        "source": "BdF (fallback)",
    },
    "cpi_yoy_pct": {
        "value": 2.1,
        "as_of": "2026-03",
        "note": "Inflation harmonisée IPCH glissement annuel",
        "source": "INSEE / BdF (fallback)",
    },
}


class BdFClient:
    """Client for the new WebStat API (v2.1)."""

    BASE_URL = "https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets"
    OBSERVATIONS_PATH = "/observations/exports/json"
    TIMEOUT = 12.0

    # Series keys we care about for the dashboard's macro chip.
    SERIES_MORTGAGE = "MIR.M.FR.B.A2C.A.R.A.2240.EUR.N"

    def __init__(self) -> None:
        self.api_key = settings.bdf_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def get_latest_observation(self, series_key: str) -> Optional[Dict[str, Any]]:
        """Latest observation for an arbitrary series_key, or None on failure."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.BASE_URL}{self.OBSERVATIONS_PATH}",
                    params={
                        "where": f'series_key="{series_key}"',
                        "order_by": "time_period_start desc",
                        "limit": 1,
                    },
                    headers={
                        "Authorization": f"Apikey {self.api_key}",
                        "Accept": "application/json",
                    },
                )
                r.raise_for_status()
                rows = r.json()
                if not rows:
                    return None
                row = rows[0]
                return {
                    "value": row.get("obs_value"),
                    "period": row.get("time_period"),
                    "title": row.get("title_fr") or row.get("title_en"),
                    "updated_at": row.get("updated_at"),
                }
        except Exception as exc:
            logger.warning(
                "BdF series fetch for %s failed (%s); falling back", series_key, exc
            )
            return None

    async def get_mortgage_rate(self) -> Dict[str, Any]:
        """Latest mean mortgage rate (TAEG)."""
        live = await self.get_latest_observation(self.SERIES_MORTGAGE)
        if live and live.get("value") is not None:
            return {
                "mortgage_rate_pct": float(live["value"]),
                "as_of": live.get("period"),
                "source": "BdF WebStat MIR (live)",
                "fetched_at": datetime.utcnow().isoformat(),
            }
        return _FALLBACKS["mortgage_rate_pct"]

    async def get_macro_snapshot(self) -> Dict[str, Any]:
        """One-call snapshot for the dashboard's macro chip."""
        mortgage = await self.get_mortgage_rate()
        return {
            "mortgage_rate": mortgage,
            "consumer_credit_rate": _FALLBACKS["consumer_credit_rate_pct"],
            "euribor_3m": _FALLBACKS["euribor_3m_pct"],
            "cpi_yoy": _FALLBACKS["cpi_yoy_pct"],
        }


bdf_client = BdFClient()

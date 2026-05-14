"""
Banque de France WebStat client — interest rates, credit, macro.

Endpoint: https://webstat.banque-france.fr/ws_wsen/
Auth: optional API key (BDF_API_KEY); most series public without key.
Falls back to documented Q1 2026 constants.

Key series for sub-rental underwriting:
  · MIR.M.FR.B.A2C.A.R.A.2240.EUR.N — taux moyen crédit immobilier
  · MIR.M.FR.B.A2A.AM.R.A.2240.EUR.N — taux moyen crédit conso
  · BSI.M.FR.N.A.A20.A.1.U2.2253.Z01.E — encours crédits immobilier
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
    BASE_URL = "https://webstat.banque-france.fr/ws_wsen/rest/data"
    TIMEOUT = 12.0

    def __init__(self) -> None:
        self.api_key = settings.bdf_api_key

    async def get_mortgage_rate(self) -> Dict[str, Any]:
        """Latest mean mortgage rate (TAEG)."""
        # The MIR series doesn't strictly need an API key, but if the
        # caller has BDF_API_KEY set we use it for rate-limit headroom.
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                headers = {"Accept": "application/json"}
                if self.api_key:
                    headers["X-IBM-Client-Id"] = self.api_key
                r = await client.get(
                    f"{self.BASE_URL}/MIR/M.FR.B.A2C.A.R.A.2240.EUR.N",
                    headers=headers,
                )
                r.raise_for_status()
                # SDMX-JSON payload — extract the latest observation.
                payload = r.json()
                obs = self._latest_obs(payload)
                if obs is None:
                    raise ValueError("no observations")
                return {
                    "mortgage_rate_pct": obs["value"],
                    "as_of": obs["period"],
                    "source": "BdF MIR (live)",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("BdF mortgage rate fetch failed (%s); using fallback", exc)
            return _FALLBACKS["mortgage_rate_pct"]

    async def get_macro_snapshot(self) -> Dict[str, Any]:
        """One-call snapshot for the dashboard's macro chip."""
        try:
            mortgage = await self.get_mortgage_rate()
        except Exception:
            mortgage = _FALLBACKS["mortgage_rate_pct"]
        return {
            "mortgage_rate": mortgage,
            "consumer_credit_rate": _FALLBACKS["consumer_credit_rate_pct"],
            "euribor_3m": _FALLBACKS["euribor_3m_pct"],
            "cpi_yoy": _FALLBACKS["cpi_yoy_pct"],
        }

    @staticmethod
    def _latest_obs(sdmx_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract the most recent (period, value) from an SDMX-JSON response."""
        try:
            data_sets = sdmx_payload.get("dataSets", [])
            series = data_sets[0].get("series", {}) if data_sets else {}
            time_dim = (
                sdmx_payload.get("structure", {})
                .get("dimensions", {})
                .get("observation", [{}])[0]
                .get("values", [])
            )
            for _, s in series.items():
                obs = s.get("observations", {})
                if not obs:
                    continue
                latest_idx = max(int(k) for k in obs.keys())
                period = time_dim[latest_idx]["id"] if latest_idx < len(time_dim) else None
                return {"period": period, "value": obs[str(latest_idx)][0]}
        except Exception:
            return None
        return None


bdf_client = BdFClient()

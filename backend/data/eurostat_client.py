"""
Eurostat client — European tourism + housing benchmarks.

Endpoint: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/
Auth: none, public.

Used for cross-border comparison context. The French dashboard's
"Versus alternatives" panel benefits from knowing where France sits
in the European cohort:
  · tour_occ_nim — nights spent in tourist accommodation by month
  · prc_hicp_manr — HICP inflation by member state
  · prc_hpi_a — house price index annual change
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


class EurostatClient:
    BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    TIMEOUT = 15.0

    @property
    def is_configured(self) -> bool:
        return True  # Public, no key

    async def get_dataset(self, code: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Generic dataset fetch. Eurostat returns SDMX-JSON."""
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.BASE_URL}{code}",
                    params={"format": "JSON", **(params or {})},
                )
                r.raise_for_status()
                return {
                    "code": code,
                    "payload": r.json(),
                    "source": f"Eurostat {code}",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("Eurostat %s fetch failed: %s", code, exc)
            return None

    async def get_french_tourism_nights(self) -> Optional[Dict[str, Any]]:
        """Latest French monthly nights spent in tourist accommodation."""
        return await self.get_dataset(
            "tour_occ_nim",
            {"geo": "FR", "lastTimePeriod": 12},
        )

    async def get_french_hpi(self) -> Optional[Dict[str, Any]]:
        """House Price Index annual change for France."""
        return await self.get_dataset(
            "prc_hpi_a",
            {"geo": "FR", "lastTimePeriod": 4},
        )


eurostat_client = EurostatClient()

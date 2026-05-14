"""
INSEE Melodi client — housing stock, population, tourism, vacancy rates.

Endpoint: https://api.insee.fr/melodi
Auth: optional. INSEE exposes a "libre" / Key Less plan that's
accessible without subscription at 30 requests/minute — INSEE's own
catalogue page reads: "accessible librement sans souscription, avec
une limite de 30 interrogations par minute." Plenty for a single
dashboard.

Modes:
  1. Anonymous (default — no INSEE_API_KEY set): hit api.insee.fr/melodi
     directly. 30 req/min anonymous cap.
  2. Authenticated (INSEE_API_KEY set): same URL, with Authorization:
     Bearer header. Higher rate limit if the operator has an approved
     subscription.

The seed fallback only kicks in on actual HTTP errors, not on missing
auth — which is the right behaviour because the "missing key" path is
itself a valid live mode.

Useful datasets:
  · DS_LOGEMENT — housing stock + vacancy by commune
  · DS_RP — recensement de la population
  · DS_TOURISM — fréquentation hôtelière + meublé touristique
  · DS_ICA — Indicateur de conjoncture d'activité
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from config import settings


logger = logging.getLogger(__name__)


class INSEEClient:
    BASE_URL = "https://api.insee.fr/melodi/data/"
    TIMEOUT = 12.0

    def __init__(self) -> None:
        self.api_key = settings.insee_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _auth_headers(self) -> Dict[str, str]:
        """Return the Authorization header when a key is set, else empty.

        Either way the call hits api.insee.fr/melodi; the only
        difference is rate limit (anonymous: 30 req/min, authenticated:
        higher).
        """
        if self.is_configured:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def get_vacancy_rate(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Logement vacant rate for a commune (5-year census base)."""
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.BASE_URL}DS_LOGEMENT/observations",
                    params={"GEO": code_insee, "INDICATEUR": "TX_LOGVAC"},
                    headers=self._auth_headers(),
                )
                r.raise_for_status()
                payload = r.json()
                obs = payload.get("observations", [])
                if not obs:
                    return self._fallback_vacancy(code_insee)
                return {
                    "code_insee": code_insee,
                    "vacancy_rate_pct": float(obs[0].get("OBS_VALUE", 0)),
                    "year": obs[0].get("TIME_PERIOD"),
                    "source": "INSEE Melodi · DS_LOGEMENT"
                    + (" (auth)" if self.is_configured else " (anonymous)"),
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("INSEE vacancy fetch failed (%s); using seed", exc)
            return self._fallback_vacancy(code_insee)

    async def get_population(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Population municipale (recensement)."""
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.BASE_URL}DS_RP/observations",
                    params={"GEO": code_insee, "INDICATEUR": "POP_MUN"},
                    headers=self._auth_headers(),
                )
                r.raise_for_status()
                payload = r.json()
                obs = payload.get("observations", [])
                return {
                    "code_insee": code_insee,
                    "population": int(obs[0].get("OBS_VALUE", 0)) if obs else None,
                    "year": obs[0].get("TIME_PERIOD") if obs else None,
                    "source": "INSEE Melodi · recensement"
                    + (" (auth)" if self.is_configured else " (anonymous)"),
                }
        except Exception as exc:
            logger.warning("INSEE population fetch failed: %s", exc)
            return None

    @staticmethod
    def _fallback_vacancy(code_insee: str) -> Dict[str, Any]:
        """When live API isn't reachable, pull from the seed corpus."""
        from data.property_seeder import load_communes
        for c in load_communes():
            if c["code_insee"] == code_insee:
                return {
                    "code_insee": code_insee,
                    "vacancy_rate_pct": c["vacancy_rate_pct"],
                    "year": "2021",
                    "source": "seed (INSEE 2021 base)",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        return {"code_insee": code_insee, "vacancy_rate_pct": None, "source": "unavailable"}


insee_client = INSEEClient()

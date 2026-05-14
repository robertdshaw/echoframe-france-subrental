"""
INSEE (Institut national de la statistique et des études économiques)
client — housing stock, population, tourism, vacancy rates.

Endpoint: https://api.insee.fr/
Auth: bearer token from data.insee.fr (free, requires registration).
Set INSEE_API_KEY to enable; falls back to seed constants otherwise.

Useful datasets for this project:
  · DS_LOGEMENT — housing stock + vacancy by commune (TR_LOGEMENT_HARMONISE)
  · DS_RP — recensement de la population (5-year cohorts)
  · DS_TOURISM — fréquentation hôtelière + meublé touristique
  · DS_ICA — Indicateur de conjoncture d'activité (commerce + services)
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

    async def get_vacancy_rate(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Logement vacant rate for a commune (5-year census base)."""
        if not self.is_configured:
            return self._fallback_vacancy(code_insee)
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                r = await client.get(
                    f"{self.BASE_URL}DS_LOGEMENT/observations",
                    params={"GEO": code_insee, "INDICATEUR": "TX_LOGVAC"},
                    headers=headers,
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
                    "source": "INSEE DS_LOGEMENT",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("INSEE vacancy fetch failed (%s); using seed", exc)
            return self._fallback_vacancy(code_insee)

    async def get_population(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Population municipale (recensement)."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.BASE_URL}DS_RP/observations",
                    params={"GEO": code_insee, "INDICATEUR": "POP_MUN"},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                r.raise_for_status()
                payload = r.json()
                obs = payload.get("observations", [])
                return {
                    "code_insee": code_insee,
                    "population": int(obs[0].get("OBS_VALUE", 0)) if obs else None,
                    "year": obs[0].get("TIME_PERIOD") if obs else None,
                    "source": "INSEE recensement",
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

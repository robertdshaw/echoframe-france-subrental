"""
Météo-France client — weather forecasts + climatology.

Endpoint: https://portail-api.meteofrance.fr/
Auth: free API key from portail-api.meteofrance.fr (registration only).
Falls back gracefully when no key set.

Why weather matters for sub-rental forecasting:
  · Ski zones (La Clusaz / Megève / Morzine / Les Gets) live and die
    by snow conditions. A poor early-season forecast tanks December
    occupancy. We want a leading indicator.
  · Lake-side zones (Annecy / Évian) see summer occupancy drop on
    rainy forecasts.
  · Heatwaves in Lyon city centre dampen short-stay demand from
    family travellers.

Useful endpoints:
  · /public/DPClim/v1/commune/{insee}/normales — climatological normals
  · /public/forecast/v1/forecast/{lat}/{lon} — 4-day daily forecast
  · /public/observations/v1/station/{station_id}/latest — current obs
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class MeteoFranceClient:
    BASE_URL = "https://public-api.meteofrance.fr/"
    TIMEOUT = 12.0

    def __init__(self) -> None:
        # We read directly from env rather than settings because this is
        # an optional source added late; saves a config.py round-trip.
        self.api_key = os.environ.get("METEOFRANCE_API_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def get_forecast(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """4-day daily forecast for a (lat, lng). Returns None on miss."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.BASE_URL}public/forecast/v1/forecast/{lat}/{lng}",
                    headers={"apikey": self.api_key},
                )
                r.raise_for_status()
                payload = r.json()
                daily = payload.get("forecast", {}).get("daily", []) or []
                return {
                    "lat": lat,
                    "lng": lng,
                    "days": [
                        {
                            "date": d.get("time", "")[:10],
                            "tmin_c": d.get("Tmin"),
                            "tmax_c": d.get("Tmax"),
                            "precip_mm": d.get("rr24"),
                            "snow_cm": d.get("snow_24h"),
                            "summary": d.get("summary"),
                        }
                        for d in daily
                    ],
                    "fetched_at": datetime.utcnow().isoformat(),
                    "source": "Météo-France public API",
                }
        except Exception as exc:
            logger.warning("Météo-France forecast for (%s,%s) failed: %s", lat, lng, exc)
            return None

    async def get_climate_normal(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Long-run climatological normals for a commune (1991-2020 base)."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.BASE_URL}public/DPClim/v1/commune/{code_insee}/normales",
                    headers={"apikey": self.api_key},
                )
                r.raise_for_status()
                return {
                    "code_insee": code_insee,
                    "normales": r.json(),
                    "source": "Météo-France DPClim",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("Météo-France normales for %s failed: %s", code_insee, exc)
            return None


meteofrance_client = MeteoFranceClient()

"""
OpenStreetMap / Nominatim client — free geocoding + reverse geocoding.

Endpoint: https://nominatim.openstreetmap.org/
No API key. Heavy rate-limit (1 req/sec); we cache aggressively.

Used for:
  · Geocoding commune names into lat/lng
  · Reverse-geocoding Airbnb scraper hits into commune codes
  · OSM polygons for zone-boundary overlays on the maps
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


class OpenStreetMapClient:
    BASE_URL = "https://nominatim.openstreetmap.org/"
    USER_AGENT = "EchoFrame-FR-Subrental/0.1 (operations@echoframe.co)"
    RATE_LIMIT_SECONDS = 1.1  # Nominatim ToS: max 1 req/s

    def __init__(self) -> None:
        self._last_request_at: float = 0.0
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """Best-match geocoding for a commune / address."""
        if query in self._cache:
            return self._cache[query]
        await self._respect_rate_limit()
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}search",
                    params={"q": query, "format": "json", "limit": 1, "countrycodes": "fr"},
                    headers={"User-Agent": self.USER_AGENT},
                )
                r.raise_for_status()
                hits = r.json()
                if not hits:
                    return None
                hit = hits[0]
                out = {
                    "query": query,
                    "lat": float(hit["lat"]),
                    "lng": float(hit["lon"]),
                    "display_name": hit.get("display_name"),
                    "fetched_at": datetime.utcnow().isoformat(),
                }
                self._cache[query] = out
                return out
        except Exception as exc:
            logger.warning("Nominatim geocode for '%s' failed: %s", query, exc)
            return None

    async def _respect_rate_limit(self) -> None:
        import time
        wait = self.RATE_LIMIT_SECONDS - (time.time() - self._last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_at = time.time()


osm_client = OpenStreetMapClient()

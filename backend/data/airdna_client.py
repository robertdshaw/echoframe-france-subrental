"""
AirDNA / AirROI / Airbtics proxy client.

AirDNA: paid (~€68/mo), proprietary scoring + RevPAR benchmarks.
        No public REST API; they expose CSV exports to subscribers and
        a JS-driven map view. Wire-up requires the operator's session
        cookie or, ideally, an AirDNA Enterprise API contract.

AirROI:  Thomas recommends as the most accurate per peer review.
         Atlas map view at https://airroi.com — partial public access.

Airbtics: "Smart zones" approach. Figures differ materially from AirDNA;
          we render BOTH when both are available and tag the source.

This file is a stub — it returns None unless an `AIRDNA_BEARER` env
var is set, in which case it tries the proprietary endpoint. The
real wire-up depends on which subscription the operator carries.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


class AirDNAClient:
    """Proxy for AirDNA / AirROI / Airbtics — operator-configurable."""

    AIRDNA_BASE = "https://api.airdna.co/v1/"  # exact path varies by sub tier
    AIRROI_BASE = "https://api.airroi.com/v1/"

    def __init__(self) -> None:
        self.airdna_token = os.environ.get("AIRDNA_BEARER")
        self.airroi_token = os.environ.get("AIRROI_BEARER")

    @property
    def is_configured(self) -> bool:
        return bool(self.airdna_token or self.airroi_token)

    async def get_zone_benchmarks(self, commune: str) -> Optional[Dict[str, Any]]:
        """Pull ADR / RevPAR / occupancy benchmarks for a commune.

        Returns None when no provider is configured. The route handler
        renders an "AirDNA: not configured" status chip instead.
        """
        if not self.is_configured:
            return None
        for fn in (self._try_airroi, self._try_airdna):
            res = await fn(commune)
            if res is not None:
                return res
        return None

    async def _try_airdna(self, commune: str) -> Optional[Dict[str, Any]]:
        if not self.airdna_token:
            return None
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(
                    f"{self.AIRDNA_BASE}market/{commune}/summary",
                    headers={"Authorization": f"Bearer {self.airdna_token}"},
                )
                r.raise_for_status()
                payload = r.json()
                return {
                    "commune": commune,
                    "adr_eur": payload.get("adr"),
                    "occupancy_pct": payload.get("occupancy_rate"),
                    "revpar_eur": payload.get("revpar"),
                    "source": "AirDNA",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("AirDNA fetch for %s failed: %s", commune, exc)
            return None

    async def _try_airroi(self, commune: str) -> Optional[Dict[str, Any]]:
        if not self.airroi_token:
            return None
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(
                    f"{self.AIRROI_BASE}city/{commune}/stats",
                    headers={"Authorization": f"Bearer {self.airroi_token}"},
                )
                r.raise_for_status()
                payload = r.json()
                return {
                    "commune": commune,
                    "adr_eur": payload.get("adr"),
                    "occupancy_pct": payload.get("occupancy"),
                    "revpar_eur": payload.get("revpar"),
                    "source": "AirROI",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("AirROI fetch for %s failed: %s", commune, exc)
            return None


airdna_client = AirDNAClient()

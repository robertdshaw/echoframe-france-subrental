"""
Regulation client — meublé touristique status per commune.

This is currently seed-driven (regulations.json) because there is no
single national API. Three official sources to wire when needed:

  · data.gouv.fr — "Déclarations de meublés de tourisme" dataset
    (per-commune registration counts, updated quarterly)
  · DGCCRF / mairie websites — changement d'usage rules
  · ADEME — DPE class distribution per commune (datagouv_client.py)

The dashboard treats this client as an interface so the seed and
live paths are interchangeable.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from data.property_seeder import load_regulations


logger = logging.getLogger(__name__)


class RegulationClient:
    async def get_commune_status(self, commune: str) -> Dict[str, Any]:
        """All known regulatory flags for a commune."""
        regs = load_regulations()
        by_commune = regs.get("by_commune", {})
        match = by_commune.get(commune) or by_commune.get(commune.title())
        if not match:
            # Fall through to a "no friction known" record so the
            # dashboard renders rather than hides the row.
            return {
                "commune": commune,
                "registration_required": False,
                "changement_usage": "unknown",
                "cap_120_days": False,
                "encadrement_loyers": False,
                "dpe_min_class": "F",
                "dpe_class_g_banned": True,
                "source": "seed (default)",
                "fetched_at": datetime.utcnow().isoformat(),
            }
        return {
            "commune": commune,
            **match,
            "source": "seed (regulations.json)",
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def get_national_constants(self) -> Dict[str, Any]:
        """National 2026 figures (micro-BIC, LMNP, CFE, taxe de séjour)."""
        return load_regulations().get("national_2026", {})


regulation_client = RegulationClient()

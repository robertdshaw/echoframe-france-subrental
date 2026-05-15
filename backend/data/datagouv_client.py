"""
data.gouv.fr client — French government open data.

Endpoint: https://www.data.gouv.fr/api/1/
No auth required for public datasets. Useful resources:

  · ADEME DPE — energy performance ratings per dwelling
    https://data.ademe.fr/datasets/dpe-v2-logements-existants
  · DVF — Demande de Valeurs Foncières (transaction prices)
    https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/
  · BPE — Base permanente des équipements (hospitals, schools, transit)
    https://www.data.gouv.fr/fr/datasets/base-permanente-des-equipements/
  · INPI registrations (numéro SIRET, business openings)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


class DataGouvClient:
    BASE_URL = "https://www.data.gouv.fr/api/1/"
    DPE_BASE_URL = "https://data.ademe.fr/data-fair/api/v1/datasets/"
    # ADEME "DPE Logements existants (depuis juillet 2021)" — verified live
    # 2026-05. The pre-2021 `dpe-france` slug is still up but has thinner,
    # older coverage; this post-2021 base is the underwriting-relevant one
    # (it's what the 2025 G-ban / 2028 F-ban policy keys off).
    DPE_DATASET = "meg-83tjwtg8dyz4vv7h1dqe"
    TIMEOUT = 15.0

    async def get_dpe_distribution(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Distribution of DPE classes (A→G) within a commune.

        Critical for sub-let underwriting since class G is banned for
        residential rental from 2025 and class F is planned for 2028.
        Returns normalised percentage shares plus the raw counts and the
        F+G ban-exposure figure. Returns None on any failure so the route
        can fall back to the dpe_distribution.json seed.
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(
                    f"{self.DPE_BASE_URL}{self.DPE_DATASET}/values_agg",
                    params={
                        "qs": f'code_insee_ban:"{code_insee}"',
                        "field": "etiquette_dpe",
                        "size": 8,
                    },
                )
                r.raise_for_status()
                payload = r.json()
                total = payload.get("total") or 0
                aggs = payload.get("aggs", []) or []
                counts = {
                    a.get("value"): a.get("total")
                    for a in aggs
                    if a.get("value") in ("A", "B", "C", "D", "E", "F", "G")
                }
                if not counts or not total:
                    return None
                shares = {
                    k: round(v / total * 100, 1) for k, v in counts.items()
                }
                f_g = round(
                    (counts.get("F", 0) + counts.get("G", 0)) / total * 100, 1
                )
                return {
                    "code_insee": code_insee,
                    "dpe_class_counts": counts,
                    "dpe_class_shares_pct": shares,
                    "f_plus_g_share_pct": f_g,
                    "n_diagnosed": total,
                    "source": "ADEME DPE Logements existants (depuis 2021) · live",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("DPE fetch for %s failed (%s); skipping", code_insee, exc)
            return None

    async def get_dvf_median_price(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Median transaction price (€/m²) from DVF for a commune.

        DVF only covers sale transactions — useful as a sanity check
        against asking rents but not a substitute.
        """
        # The CSV-shipped DVF is not easily queryable via API; we ship
        # a placeholder that returns None so the dashboard falls back
        # to its seed constants. Wire-up via the cadastre-stats helper
        # at app.dvf.etalab.gouv.fr/api is one Phase-7 method call.
        return None


datagouv_client = DataGouvClient()

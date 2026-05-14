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
    TIMEOUT = 12.0

    async def get_dpe_distribution(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Distribution of DPE classes (A→G) within a commune.

        Critical for sub-let underwriting since class G is banned for
        residential rental from 2025 and class F is planned for 2028.
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                # ADEME publishes the DPE base on data-fair; the dataset
                # slug and exact param names move occasionally — wired
                # here against the documented public endpoint.
                r = await client.get(
                    f"{self.DPE_BASE_URL}dpe-v2-logements-existants/values_agg",
                    params={
                        "qs": f'"Code_INSEE_(BAN)":"{code_insee}"',
                        "field": "Etiquette_DPE",
                        "size": 7,
                    },
                )
                r.raise_for_status()
                payload = r.json()
                aggs = payload.get("aggs", []) or []
                dist = {a.get("value"): a.get("total") for a in aggs}
                return {
                    "code_insee": code_insee,
                    "dpe_class_counts": dist,
                    "source": "ADEME DPE v2",
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

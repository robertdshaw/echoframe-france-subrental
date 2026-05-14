"""
DVF (Demandes de Valeurs Foncières) client — real French property
transaction prices.

Endpoint: https://api.cadastre.data.gouv.fr/  (no auth required)
         https://app.dvf.etalab.gouv.fr/api/   (no auth required)

DVF publishes the official register of all French property transactions
since 2014. Critical for landlord-side underwriting because it gives
*actual* sale prices per commune, not asking prices.

For sub-rental we use it to:
  · Sanity-check seloger asking rents against transaction-derived
    yield benchmarks
  · Project landlord acquisition costs when modelling owner economics
  · Surface emerging price trends that haven't hit MLS asking-price
    distributions yet

Useful endpoints:
  · GET /api/mutations3/{code_insee} — all transactions for a commune
  · GET /api/cadastre/parcelle/{cadastre_id} — parcel-level history
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class DVFClient:
    BASE_URL = "https://app.dvf.etalab.gouv.fr/api/"
    TIMEOUT = 15.0

    @property
    def is_configured(self) -> bool:
        # No auth required — always "configured" as long as the endpoint
        # is reachable. We still expose this property for API symmetry.
        return True

    async def get_commune_summary(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Median €/m² + transaction count for a commune (last 2 years)."""
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(f"{self.BASE_URL}mutations3/{code_insee}")
                r.raise_for_status()
                payload = r.json()
                # The DVF payload contains a list of mutations under
                # 'mutations'; each has 'valeur_fonciere' and
                # 'surface_reelle_bati'. We compute median €/m² over the
                # most recent 24 months.
                mutations = payload.get("mutations", []) or []
                prices_per_m2 = [
                    float(m["valeur_fonciere"]) / float(m["surface_reelle_bati"])
                    for m in mutations
                    if m.get("valeur_fonciere")
                    and m.get("surface_reelle_bati")
                    and float(m.get("surface_reelle_bati") or 0) > 0
                ][-500:]  # cap at most recent 500 to bound cost
                if not prices_per_m2:
                    return None
                return {
                    "code_insee": code_insee,
                    "median_price_per_m2_eur": round(statistics.median(prices_per_m2), 0),
                    "n_transactions": len(prices_per_m2),
                    "source": "DVF (etalab)",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
        except Exception as exc:
            logger.warning("DVF fetch for %s failed: %s", code_insee, exc)
            return None


dvf_client = DVFClient()

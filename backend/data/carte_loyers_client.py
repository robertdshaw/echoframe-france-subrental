"""
Carte des loyers client — official per-commune rent indicator.

Replaces the SeLoger / LeBonCoin scraper, which was impossible: both
sites sit behind DataDome and return 403 + CAPTCHA to any server-side
request (verified 2026-05). Scraping them from a datacenter IP — let
alone Render — does not work and never will without a paid unblocker.

The French housing ministry (DHUP) + ANIL publish an *official*
modelled rent indicator per commune on data.gouv.fr: predicted asking
rent €/m² for apartments, with a 95% interval and an observation
count. It is free, keyless, has no anti-bot, covers ~34,900 communes,
and is refreshed annually. It is a strictly better long-term-rent
source than scraping listings.

Cost: €0. It is a static government CSV download. Worst case (Render's
ephemeral disk drops the in-process cache on a cold start) is a single
~4.7 MB re-download — still free. There is no per-call billing anywhere
in this module. Contrast [[apify-cost-incident]].

Resolution: the dataset slug is stable
(`carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025`);
we resolve the all-apartment CSV resource via the data.gouv API rather
than hardcoding the date-stamped static URL, which rotates on republish.

Fallback chain: in-memory (process lifetime) → committed seed
`seeds/rent_benchmark.json` (real 2025 values, not synthetic) → and the
live refresh only *upgrades* that. A live failure never breaks a
caller; it just keeps serving the committed official values.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).parent / "seeds" / "rent_benchmark.json"
DATASET_SLUG = (
    "carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025"
)
DATASET_API = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_SLUG}/"
DOWNLOAD_TIMEOUT = 60.0


def _to_float(s: Optional[str]) -> Optional[float]:
    s = (s or "").strip().strip('"')
    if not s:
        return None
    try:
        return round(float(s.replace(",", ".")), 2)
    except ValueError:
        return None


class CarteLoyersClient:
    """Official commune rent €/m². Seed-backed, optionally live-refreshed."""

    def __init__(self) -> None:
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._provenance: str = "seed"

    # ---- load paths -------------------------------------------------

    def _load_seed(self) -> Dict[str, Dict[str, Any]]:
        with _SEED_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh).get("by_code_insee", {})

    def _wanted_insee(self) -> Dict[str, str]:
        """Our communes only — we never parse all 34,900 rows into memory."""
        communes_path = _SEED_PATH.parent / "communes.json"
        with communes_path.open("r", encoding="utf-8") as fh:
            return {c["code_insee"]: c["name"] for c in json.load(fh)}

    def _resolve_csv_url(self) -> Optional[str]:
        try:
            ds = httpx.get(DATASET_API, timeout=20.0).json()
        except Exception as exc:
            logger.warning("Carte des loyers dataset resolve failed: %s", exc)
            return None
        for r in ds.get("resources", []) or []:
            title = (r.get("title") or "").lower()
            if (
                r.get("format") == "csv"
                and "appartement" in title
                and "pièces" not in title
                and "1 ou 2" not in title
            ):
                return r.get("url")
        return None

    def refresh(self) -> bool:
        """Pull the latest official CSV, extract our communes, cache it.

        Returns True if the live refresh succeeded. Free; safe to fail.
        """
        url = self._resolve_csv_url()
        if not url:
            return False
        try:
            raw = httpx.get(url, timeout=DOWNLOAD_TIMEOUT).content.decode(
                "latin-1"
            )
        except Exception as exc:
            logger.warning("Carte des loyers CSV download failed: %s", exc)
            return False

        want = self._wanted_insee()
        rows = csv.reader(io.StringIO(raw), delimiter=";")
        header = next(rows, None)
        if not header:
            return False
        ci = {h: i for i, h in enumerate(header)}
        needed = ("INSEE_C", "loypredm2", "lwr.IPm2", "upr.IPm2", "TYPPRED")
        if any(k not in ci for k in needed):
            logger.warning("Carte des loyers CSV schema changed: %s", header)
            return False

        extracted: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            code = row[ci["INSEE_C"]].strip().strip('"')
            if code not in want:
                continue
            extracted[code] = {
                "commune": want[code],
                "rent_eur_per_m2": _to_float(row[ci["loypredm2"]]),
                "ci_low": _to_float(row[ci["lwr.IPm2"]]),
                "ci_high": _to_float(row[ci["upr.IPm2"]]),
                "pred_type": row[ci["TYPPRED"]].strip().strip('"'),
                "n_obs_commune": (
                    int(float(row[ci["nbobs_com"]]))
                    if "nbobs_com" in ci and row[ci["nbobs_com"]].strip()
                    else None
                ),
            }
        if not extracted:
            return False
        self._cache = extracted
        self._provenance = "live (data.gouv Carte des loyers 2025)"
        logger.info("Carte des loyers refreshed: %d communes", len(extracted))
        return True

    def _ensure_loaded(self) -> None:
        if self._cache is not None:
            return
        # Try a one-time live refresh per process; fall back to the
        # committed official seed. Either way the values are real.
        if not self.refresh():
            self._cache = self._load_seed()
            self._provenance = "seed (official 2025 vintage)"

    # ---- public API -------------------------------------------------

    def get_rent_per_m2(self, code_insee: str) -> Optional[Dict[str, Any]]:
        """Predicted asking rent €/m² for a commune, or None if unknown."""
        self._ensure_loaded()
        rec = (self._cache or {}).get(code_insee)
        if not rec or rec.get("rent_eur_per_m2") is None:
            return None
        return {
            "code_insee": code_insee,
            **rec,
            "provenance": self._provenance,
            "source": "data.gouv.fr · Carte des loyers 2025 (DHUP/ANIL)",
        }


carte_loyers_client = CarteLoyersClient()

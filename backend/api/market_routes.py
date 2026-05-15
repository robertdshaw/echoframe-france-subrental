"""Comp listings + market-overview routes.

Data layering principle (matches the README anti-hallucination rules):
every endpoint prefers a live source, falls back to seed, and tags the
provenance on the response so the dashboard can render a 'live · seed'
chip. A live failure never breaks the endpoint.
"""

from __future__ import annotations

import asyncio
import statistics
from typing import Any, Dict, List

from fastapi import APIRouter

from api.schemas import CompListing
from data.airroi_client import airroi_client
from data.carte_loyers_client import carte_loyers_client
from data.datagouv_client import datagouv_client
from data.eurostat_client import eurostat_client
from data.property_seeder import (
    load_airbnb_comps,
    load_communes,
    load_dpe_distribution,
    load_monthly_str_series,
    load_rental_comps,
    load_zones,
)

router = APIRouter(prefix="/api/market", tags=["market"])


def _commune_insee(slug: str) -> Dict[str, str]:
    """commune name → code_insee for one zone (from the commune seed)."""
    return {
        c["name"]: c["code_insee"]
        for c in load_communes()
        if c["zone_slug"] == slug
    }


@router.get("/zones/{slug}/airbnb-comps", response_model=List[CompListing])
async def airbnb_comps(slug: str) -> List[CompListing]:
    """Airbnb comps for the zone, from the curated seed corpus.

    The Apify live-scrape path was removed after it ran unbounded
    (the actor ignored the per-call item cap and the Render cache is
    ephemeral, so every request re-scraped whole cities — ~$50 in one
    session). Comps are seed-only by design now; there is no per-call
    cost. See data-sources status for provenance.
    """
    return [CompListing(**c) for c in load_airbnb_comps(slug)]


@router.get("/zones/{slug}/rental-comps", response_model=List[CompListing])
async def rental_comps(slug: str) -> List[CompListing]:
    """Long-term rental comps for the zone.

    The rental seed carries `source_platform` (SeLoger / LeBonCoin / PAP)
    rather than the `source` field CompListing requires — map it across
    so the response validates instead of 500-ing (pre-existing bug).
    """
    out: List[CompListing] = []
    for c in load_rental_comps(slug):
        rec = dict(c)
        rec.setdefault("source", rec.get("source_platform", "seed"))
        out.append(CompListing(**rec))
    return out


@router.get("/zones/{slug}/spread")
async def airbnb_landlord_spread(slug: str):
    """Per-commune Airbnb-revenue minus landlord-rent spread.

    Airbnb side: seed comps (Apify removed). Rent side: the official
    Carte des loyers €/m² (DHUP/ANIL, free, no key) applied to the
    median comp size, with the seed rent_monthly kept as a cross-check.
    Each row carries both numbers + which one drove the headline spread
    so nothing is silently fabricated.
    """
    ab = load_airbnb_comps(slug)
    rc = load_rental_comps(slug)
    insee = _commune_insee(slug)
    by_commune: dict[str, dict] = {}
    for c in ab:
        com = c["commune"]
        by_commune.setdefault(com, {"airbnb": [], "rental": []})["airbnb"].append(c)
    for r in rc:
        com = r["commune"]
        by_commune.setdefault(com, {"airbnb": [], "rental": []})["rental"].append(r)
    rows = []
    for com, buckets in by_commune.items():
        if not buckets["airbnb"] or not buckets["rental"]:
            continue
        adrs = [x["adr_eur"] for x in buckets["airbnb"] if x.get("adr_eur")]
        occs = [
            x["occupancy_pct"]
            for x in buckets["airbnb"]
            if x.get("occupancy_pct") is not None
        ]
        if not adrs or not occs:
            continue
        med_adr = statistics.median(adrs)
        med_occ = statistics.median(occs)
        airbnb_annual = med_adr * 365 * (med_occ / 100)

        rents = [x["rent_monthly"] for x in buckets["rental"] if x.get("rent_monthly")]
        sizes = [x["size_m2"] for x in buckets["rental"] if x.get("size_m2")]
        if not rents:
            continue
        seed_rental_annual = statistics.median(rents) * 12

        # Official rent anchor: €/m² × median comp size × 12.
        official_rental_annual = None
        official = (
            carte_loyers_client.get_rent_per_m2(insee[com])
            if com in insee
            else None
        )
        if official and sizes:
            official_rental_annual = (
                official["rent_eur_per_m2"] * statistics.median(sizes) * 12
            )

        # Prefer the official anchor for the headline spread; fall back
        # to the seed rent when the commune isn't in the ministry model.
        rental_annual = official_rental_annual or seed_rental_annual
        rent_basis = "official_carte_loyers" if official_rental_annual else "seed"

        rows.append({
            "commune": com,
            "airbnb_annual_eur": round(airbnb_annual, 0),
            "rental_annual_eur": round(rental_annual, 0),
            "rental_annual_seed_eur": round(seed_rental_annual, 0),
            "rental_annual_official_eur": (
                round(official_rental_annual, 0) if official_rental_annual else None
            ),
            "rent_eur_per_m2_official": official["rent_eur_per_m2"] if official else None,
            "rent_basis": rent_basis,
            "spread_eur": round(airbnb_annual - rental_annual, 0),
            "spread_multiple": round(airbnb_annual / rental_annual, 2) if rental_annual else None,
            "n_airbnb_comps": len(buckets["airbnb"]),
            "n_rental_comps": len(buckets["rental"]),
        })
    rows.sort(key=lambda r: r["spread_eur"], reverse=True)
    return {
        "zone_slug": slug,
        "rent_provenance": carte_loyers_client._provenance,
        "by_commune": rows,
    }


@router.get("/zones/{slug}/rent-benchmark")
async def rent_benchmark(slug: str):
    """Official predicted asking rent €/m² per commune for the zone.

    Source: data.gouv.fr "Carte des loyers" 2025 (DHUP/ANIL ministry
    model) — free, keyless, no anti-bot, ~34,900 communes, refreshed
    annually. This replaces the SeLoger/LeBonCoin scrape, which is
    impossible server-side (both are DataDome-walled). Live-refreshed
    once per process with the committed official seed as fallback.
    """
    insee = _commune_insee(slug)
    out = []
    for name, code in insee.items():
        rec = carte_loyers_client.get_rent_per_m2(code)
        if not rec:
            out.append({"commune": name, "code_insee": code, "rent_eur_per_m2": None})
            continue
        out.append({
            "commune": name,
            "code_insee": code,
            "rent_eur_per_m2": rec["rent_eur_per_m2"],
            "ci_low": rec.get("ci_low"),
            "ci_high": rec.get("ci_high"),
            "pred_type": rec.get("pred_type"),
            "n_obs_commune": rec.get("n_obs_commune"),
        })
    vals = [r["rent_eur_per_m2"] for r in out if r["rent_eur_per_m2"]]
    return {
        "zone_slug": slug,
        "zone_median_eur_per_m2": round(statistics.median(vals), 2) if vals else None,
        "provenance": carte_loyers_client._provenance,
        "source": "data.gouv.fr · Carte des loyers 2025 (DHUP/ANIL)",
        "by_commune": out,
    }


@router.get("/zones/{slug}/monthly-series")
async def monthly_str_series(slug: str):
    """24-month ADR + occupancy trajectory for a zone.

    Live AirROI when configured (and the zone is mapped), else the
    derived seed series. Either way the response carries a `provenance`
    field so the chart can label itself honestly.
    """
    seed = load_monthly_str_series(slug)
    benchmarks = await airroi_client.get_zone_benchmarks(slug)
    if benchmarks:
        return {
            "zone_slug": slug,
            "as_of_month": seed.get("as_of_month"),
            "series": seed.get("series", []),
            "live_benchmark": {
                "adr_eur_trailing_12mo": benchmarks.get("adr_eur_trailing_12mo"),
                "occupancy_pct_trailing_12mo": benchmarks.get("occupancy_pct_trailing_12mo"),
                "revpar_eur_trailing_12mo": benchmarks.get("revpar_eur_trailing_12mo"),
                "avg_monthly_revenue_eur": benchmarks.get("avg_monthly_revenue_eur"),
                "proxy_note": benchmarks.get("proxy_note"),
            },
            "provenance": "seed series + live AirROI 12-mo anchor",
            "source": benchmarks.get("source"),
        }
    return {
        "zone_slug": slug,
        "as_of_month": seed.get("as_of_month"),
        "series": seed.get("series", []),
        "live_benchmark": None,
        "provenance": "seed (AirROI not configured / zone not covered)",
        "source": seed.get("source"),
    }


@router.get("/zones/{slug}/dpe")
async def zone_dpe_distribution(slug: str):
    """DPE class distribution across the zone's communes.

    Live ADEME per-commune (verified working endpoint), with the
    dpe_distribution.json seed as a per-commune fallback. Surfaces the
    F+G ban-exposure share, which is the underwriting-relevant number
    (G banned 2025, F banned 2028).
    """
    communes = [c for c in load_communes() if c["zone_slug"] == slug]
    seed_doc = load_dpe_distribution()
    seed_by_insee = seed_doc.get("by_code_insee", {})

    async def _one(commune: Dict[str, Any]) -> Dict[str, Any]:
        insee = commune["code_insee"]
        live = await datagouv_client.get_dpe_distribution(insee)
        if live:
            return {
                "commune": commune["name"],
                "code_insee": insee,
                "shares_pct": live["dpe_class_shares_pct"],
                "f_plus_g_share_pct": live["f_plus_g_share_pct"],
                "n_diagnosed": live["n_diagnosed"],
                "provenance": "live",
                "source": live["source"],
            }
        s = seed_by_insee.get(insee, {})
        if not s:
            return {
                "commune": commune["name"],
                "code_insee": insee,
                "shares_pct": {},
                "f_plus_g_share_pct": None,
                "n_diagnosed": None,
                "provenance": "unavailable",
                "source": None,
            }
        shares = {k: s[k] for k in ("A", "B", "C", "D", "E", "F", "G") if k in s}
        return {
            "commune": commune["name"],
            "code_insee": insee,
            "shares_pct": shares,
            "f_plus_g_share_pct": round(s.get("F", 0) + s.get("G", 0), 1),
            "n_diagnosed": s.get("n"),
            "provenance": "seed",
            "source": s.get("source"),
        }

    rows = await asyncio.gather(*[_one(c) for c in communes])
    valid = [r for r in rows if r["f_plus_g_share_pct"] is not None]
    zone_fg = (
        round(statistics.mean([r["f_plus_g_share_pct"] for r in valid]), 1)
        if valid
        else None
    )
    return {
        "zone_slug": slug,
        "national_context": seed_doc.get("national_2026_context", {}),
        "zone_avg_f_plus_g_pct": zone_fg,
        "by_commune": list(rows),
    }


@router.get("/eurostat-context")
async def eurostat_context():
    """France tourism-nights + house-price-index cross-border context.

    Public Eurostat, no key. Powers the 'Versus alternatives' panel's
    macro backdrop. Degrades to nulls (never errors) if Eurostat is
    unreachable.
    """
    nights, hpi = await asyncio.gather(
        eurostat_client.get_french_tourism_nights(),
        eurostat_client.get_french_hpi(),
    )

    def _latest(payload: Any) -> Any:
        if not payload:
            return None
        body = payload.get("payload") or {}
        values = body.get("value") or {}
        if not values:
            return None
        last_key = sorted(values.keys(), key=lambda k: int(k))[-1]
        return values.get(last_key)

    return {
        "tourism_nights_latest": _latest(nights),
        "house_price_index_latest": _latest(hpi),
        "tourism_source": (nights or {}).get("source"),
        "hpi_source": (hpi or {}).get("source"),
        "provenance": "live Eurostat" if (nights or hpi) else "unavailable",
    }


@router.get("/overview")
async def market_overview():
    """Cross-zone summary for the market-research landing page."""
    return {
        "zones": load_zones(),
        "data_sources": [
            {"name": "AirROI", "cost_eur_monthly": 10, "note": "Primary STR · live monthly series · 5/7 zones"},
            {"name": "Airbnb comps", "cost_eur_monthly": 0, "note": "Curated seed corpus (Apify removed — ran unbounded)"},
            {"name": "ADEME DPE", "cost_eur_monthly": 0, "note": "Live per-commune DPE distribution · F+G ban exposure"},
            {"name": "Eurostat", "cost_eur_monthly": 0, "note": "Live tourism-nights + HPI macro context"},
        ],
    }

"""
Property scorer — turns a concrete flat (commune, asking rent, size)
into a sub-rental decision: projected margin, spread vs the *official*
market rent, DPE ban exposure, regulatory friction, a verdict, and the
back-solved offer to make the landlord to hit a target margin.

Every number traces to a real source (anti-hallucination rule):
  · Airbnb side  — zone 24-month ADR/occupancy series (seed-derived,
    real French seasonality; the same series the forecast uses)
  · Rent side    — official Carte des loyers €/m² (DHUP/ANIL, free)
  · DPE risk     — ADEME distribution seed per commune
  · Friction     — zone regulatory_friction
  · Margin       — the French cost-stack engine (margin_calculator)

There is NO scraping and NO per-call cost here. The "find specific
flats" part is deliberately NOT automated — DataDome walls SeLoger /
LeBonCoin and the only bypass is the paid scraper that already cost
~$50 (see [[apify-cost-incident]]). The operator imports a real flat
they sourced; this module scores it against real market data.
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

from data.carte_loyers_client import carte_loyers_client
from data.property_seeder import (
    load_communes,
    load_dpe_distribution,
    load_monthly_str_series,
    load_zones,
)
from services.margin_calculator import MarginInputs, compute_margin


# Reference unit capacity by French type label when `capacity` is absent.
_CAPACITY_BY_TYPE = {
    "studio": 2,
    "t1": 2,
    "t2": 4,
    "t3": 5,
    "t4": 6,
    "t5": 8,
    "maison": 8,
    "chalet": 8,
}

# Target net margin the offer back-solve aims to preserve. Operator can
# override per call; 18% is the modal break-even-plus band operators
# accept for a managed sub-let after the full French cost stack.
DEFAULT_TARGET_MARGIN_PCT = 18.0


def _zone_by_commune() -> Dict[str, Dict[str, str]]:
    """commune name → {zone_slug, code_insee}."""
    return {
        c["name"]: {"zone_slug": c["zone_slug"], "code_insee": c["code_insee"]}
        for c in load_communes()
    }


def _zone_adr_occ(zone_slug: str) -> tuple[Optional[float], Optional[float]]:
    """Trailing-12-month median ADR & occupancy from the 24-mo series."""
    series = load_monthly_str_series(zone_slug).get("series", [])
    if not series:
        zones = {z["slug"]: z for z in load_zones()}
        z = zones.get(zone_slug)
        if not z:
            return None, None
        return z["median_adr_eur"], z["median_occupancy_pct"]
    last12 = series[-12:]
    return (
        statistics.median([s["adr_eur"] for s in last12]),
        statistics.median([s["occupancy_pct"] for s in last12]),
    )


def _capacity(prop: Dict[str, Any]) -> int:
    if prop.get("capacity"):
        return int(prop["capacity"])
    t = str(prop.get("type") or "").strip().lower()
    if t in _CAPACITY_BY_TYPE:
        return _CAPACITY_BY_TYPE[t]
    rooms = prop.get("rooms")
    if rooms:
        return max(2, int(rooms) + 1)
    return 4


def _verdict(net_pct: float, friction: str) -> str:
    if net_pct >= 12 and friction != "high":
        return "TARGET"
    if net_pct >= 6:
        return "WAIT"
    return "AVOID"


def _max_rent_for_target(
    base: MarginInputs, target_pct: float, charges_ratio: float
) -> Optional[float]:
    """Bisect the monthly rent that yields exactly `target_pct` net margin.

    Higher rent → lower margin (monotone), so a clean bisection works.
    Returns None if even €1 rent can't reach the target (deal is dead).
    """
    lo, hi = 1.0, 20000.0

    def margin_at(rent: float) -> float:
        r = compute_margin(
            MarginInputs(
                adr_eur=base.adr_eur,
                occupancy_pct=base.occupancy_pct,
                capacity=base.capacity,
                rent_monthly_eur=rent,
                charges_monthly_eur=rent * charges_ratio,
            )
        )
        return r.net_margin_pct_of_revenue

    if margin_at(lo) < target_pct:
        return None
    for _ in range(40):
        mid = (lo + hi) / 2
        if margin_at(mid) >= target_pct:
            lo = mid
        else:
            hi = mid
    return round(lo, 0)


def score_property(
    prop: Dict[str, Any],
    target_margin_pct: float = DEFAULT_TARGET_MARGIN_PCT,
) -> Dict[str, Any]:
    """Score one flat. `prop` needs: commune, size_m2, rent_monthly;
    optional: type, rooms, capacity, charges, dpe_class, zone_slug, id.

    Returns a flat dict safe to serialise; on missing market data it
    degrades to nulls with a `data_gaps` list rather than inventing.
    """
    gaps: List[str] = []
    cmap = _zone_by_commune()
    commune = prop.get("commune")
    meta = cmap.get(commune or "")
    zone_slug = prop.get("zone_slug") or (meta or {}).get("zone_slug")
    code_insee = (meta or {}).get("code_insee")

    zones = {z["slug"]: z for z in load_zones()}
    zone = zones.get(zone_slug or "")
    friction = (zone or {}).get("regulatory_friction", "unknown")

    adr, occ = _zone_adr_occ(zone_slug) if zone_slug else (None, None)
    if adr is None or occ is None:
        gaps.append("no zone ADR/occupancy series for this commune")

    asking_rent = prop.get("rent_monthly")
    size = prop.get("size_m2")
    charges = prop.get("charges")
    charges_ratio = (
        (charges / asking_rent) if (charges and asking_rent) else 0.07
    )

    # Official market rent for the commune (free, cached).
    official = (
        carte_loyers_client.get_rent_per_m2(code_insee) if code_insee else None
    )
    market_rent_monthly = None
    if official and official.get("rent_eur_per_m2") and size:
        market_rent_monthly = round(official["rent_eur_per_m2"] * size, 0)
    else:
        gaps.append("no official Carte des loyers rent for this commune/size")

    # Margin at the asking rent.
    margin = None
    if adr is not None and occ is not None and asking_rent:
        m = compute_margin(
            MarginInputs(
                adr_eur=adr,
                occupancy_pct=occ,
                capacity=_capacity(prop),
                rent_monthly_eur=asking_rent,
                charges_monthly_eur=asking_rent * charges_ratio,
            )
        )
        margin = {
            "gross_revenue_annual_eur": m.gross_revenue_annual_eur,
            "net_margin_annual_eur": m.net_margin_annual_eur,
            "net_margin_pct": round(m.net_margin_pct_of_revenue, 2),
        }

    # DPE ban exposure for the commune (seed distribution, free).
    dpe = load_dpe_distribution(code_insee) if code_insee else {}
    f_plus_g = (
        round(dpe.get("F", 0) + dpe.get("G", 0), 1) if dpe else None
    )
    prop_dpe = (prop.get("dpe_class") or "").upper().strip()
    dpe_blocked = prop_dpe in ("G",) or (prop_dpe == "F")  # G banned 2025, F 2028

    # Landlord-offer back-solve.
    offer = None
    if adr is not None and occ is not None:
        base = MarginInputs(
            adr_eur=adr,
            occupancy_pct=occ,
            capacity=_capacity(prop),
            rent_monthly_eur=asking_rent or (market_rent_monthly or 1000),
            charges_monthly_eur=0.0,
        )
        max_rent = _max_rent_for_target(base, target_margin_pct, charges_ratio)
        if max_rent:
            offer = {
                "target_margin_pct": target_margin_pct,
                "max_rent_offer_monthly_eur": max_rent,
                "vs_asking_rent_eur": (
                    round(max_rent - asking_rent, 0) if asking_rent else None
                ),
                "vs_official_market_pct": (
                    round((max_rent / market_rent_monthly - 1) * 100, 1)
                    if market_rent_monthly
                    else None
                ),
                "interpretation": (
                    "can offer a premium over market - strong acceptance lever"
                    if market_rent_monthly and max_rent > market_rent_monthly
                    else "must offer at/below market - acceptance harder, lean on hands-off pitch"
                ),
            }
        else:
            offer = {
                "target_margin_pct": target_margin_pct,
                "max_rent_offer_monthly_eur": None,
                "interpretation": "no rent clears the target margin - deal not viable here",
            }

    net_pct = margin["net_margin_pct"] if margin else -999
    verdict = _verdict(net_pct, friction) if margin else "INSUFFICIENT_DATA"
    if dpe_blocked and verdict != "INSUFFICIENT_DATA":
        verdict = "AVOID"
        gaps.append(
            f"DPE class {prop_dpe} is banned for letting "
            f"({'2025' if prop_dpe == 'G' else '2028'}) — disqualifying"
        )

    spread_multiple = None
    if margin and market_rent_monthly:
        ab_annual = margin["gross_revenue_annual_eur"]
        spread_multiple = round(ab_annual / (market_rent_monthly * 12), 2)

    return {
        "property_id": prop.get("id"),
        "commune": commune,
        "zone_slug": zone_slug,
        "type": prop.get("type"),
        "size_m2": size,
        "asking_rent_monthly_eur": asking_rent,
        "official_market_rent_monthly_eur": market_rent_monthly,
        "official_rent_eur_per_m2": (official or {}).get("rent_eur_per_m2"),
        "zone_adr_eur": round(adr, 1) if adr else None,
        "zone_occupancy_pct": round(occ, 1) if occ else None,
        "margin": margin,
        "spread_multiple": spread_multiple,
        "dpe_class": prop_dpe or None,
        "commune_f_plus_g_pct": f_plus_g,
        "dpe_letting_blocked": dpe_blocked,
        "regulatory_friction": friction,
        "verdict": verdict,
        "landlord_offer": offer,
        "rent_provenance": carte_loyers_client._provenance,
        "data_gaps": gaps,
    }


def rank_properties(
    props: List[Dict[str, Any]],
    target_margin_pct: float = DEFAULT_TARGET_MARGIN_PCT,
) -> List[Dict[str, Any]]:
    """Score a list of flats and rank best-first.

    Sort key: viable verdict, then net margin €, then occupancy. Flats
    with insufficient data sink to the bottom rather than being dropped
    (the operator still needs to see they were considered).
    """
    scored = [score_property(p, target_margin_pct) for p in props]

    def sort_key(s: Dict[str, Any]):
        viable = 1 if s["verdict"] in ("TARGET", "WAIT") else 0
        net = (s.get("margin") or {}).get("net_margin_annual_eur") or -1e9
        occ = s.get("zone_occupancy_pct") or 0
        return (viable, net, occ)

    scored.sort(key=sort_key, reverse=True)
    for i, s in enumerate(scored, 1):
        s["rank"] = i
    return scored

"""
Airbnb scraper — Apify-backed, with a 24-hour disk cache.

How it works:
  1. For each zone we have a primary search term (commune name) that
     Apify's Airbnb actor understands as a location query.
  2. We run `tri_angle/new-fast-airbnb-scraper` (or whatever
     APIFY_AIRBNB_ACTOR_ID overrides it to) with that location.
  3. Results are mapped to our `CompListing` shape and written to
     backend/data/cache/airbnb/{zone}_{YYYY-MM-DD}.json.
  4. The next request the same day reads from cache — no Apify call.

Cost control:
  · Actor pricing: $0.50 per 1,000 results.
  · LIMIT_PER_ZONE = 25, 7 zones, daily refresh = 5,250 results / month
    ≈ $2.60 / month worst case. The cache keeps this from running away.
  · Fail-safe: any error in Apify path returns None so the route falls
    back to seed comps. Never break the dashboard for a scraper hiccup.

Actor I/O reference (from Apify Store, May 2026):
  Input  : {"locationQueries": ["Lyon"], "maxItems": 25, "currency": "EUR"}
  Output (per item):
    {
      "id": "12345",
      "url": "https://www.airbnb.com/rooms/12345",
      "name": "Loft near Vieux Lyon",
      "roomType": "Entire home/apt",
      "personCapacity": 4,
      "coordinates": {"latitude": 45.76, "longitude": 4.83},
      "pricing": {"price": 142},
      "rating": {"average": 4.84, "reviewsCount": 137}
    }
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from data.apify_client import apify_client
from data.property_seeder import load_airbnb_comps


logger = logging.getLogger(__name__)


# Apify location query per zone slug. Pick the most-recognised commune in
# each zone — Apify's location resolver works best with names a casual
# searcher would type into airbnb.com.
ZONE_SEARCH_TERMS: Dict[str, str] = {
    "pays-de-gex": "Ferney-Voltaire",
    "annecy-haute-savoie": "Annecy",
    "greater-lyon": "Lyon",
    "grenoble-isere": "Grenoble",
    "dijon-cote-dor": "Dijon",
    "ski-access": "Megève",
    "geneva-periphery": "Annemasse",
}

LIMIT_PER_ZONE = 25
CACHE_DIR = Path(__file__).parent / "cache" / "airbnb"
DEFAULT_ACTOR_ID = "tri_angle/new-fast-airbnb-scraper"


def _cache_path(zone_slug: str, day: Optional[str] = None) -> Path:
    day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return CACHE_DIR / f"{zone_slug}_{day}.json"


def _read_cache(zone_slug: str) -> Optional[List[Dict[str, Any]]]:
    path = _cache_path(zone_slug)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Cache read failed for %s: %s", zone_slug, exc)
        return None


def _write_cache(zone_slug: str, comps: List[Dict[str, Any]]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(zone_slug)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(comps, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Cache write failed for %s: %s", zone_slug, exc)


def _occupancy_proxy(rating: Optional[float], reviews: Optional[int]) -> Optional[float]:
    """Estimate occupancy% from review count (we can't see calendars).

    A 4-star listing with 100+ reviews has been booked a lot; 4.7+ with
    200+ reviews is a workhorse. This is a coarse proxy — caller should
    treat it as illustrative, not truth. Used only to colour the map
    consistently with the rest of the dashboard's occupancy axis.
    """
    if reviews is None:
        return None
    if reviews >= 200:
        return 78.0
    if reviews >= 100:
        return 70.0
    if reviews >= 50:
        return 62.0
    if reviews >= 20:
        return 55.0
    return 45.0


def _commune_from_address(item: Dict[str, Any], zone_search: str) -> str:
    """Best-effort commune label for the listing.

    Apify's Airbnb actor exposes the searched location, not always the
    exact commune. We use the zone's primary search term as the label
    rather than scraping address fields — it's accurate at zone level
    even when the actor returns suburb-level lat/lng.
    """
    return (
        item.get("locality")
        or item.get("city")
        or zone_search
    )


def _normalise(item: Dict[str, Any], zone_slug: str, zone_search: str) -> Optional[Dict[str, Any]]:
    """Map one Apify result to our CompListing dict shape.

    Skips entries missing coordinates or price — those can't render on
    the map and aren't useful for the spread calc either.
    """
    coords = item.get("coordinates") or {}
    lat = coords.get("latitude") or coords.get("lat")
    lng = coords.get("longitude") or coords.get("lng") or coords.get("lon")
    pricing = item.get("pricing") or {}
    price = pricing.get("price") or pricing.get("rate") or item.get("price")
    if lat is None or lng is None or price is None:
        return None

    rating_obj = item.get("rating") or {}
    rating = rating_obj.get("average") if isinstance(rating_obj, dict) else None
    reviews = rating_obj.get("reviewsCount") if isinstance(rating_obj, dict) else None

    listing_id = item.get("id") or item.get("listingId") or item.get("url", "")
    return {
        "id": f"apify_{listing_id}",
        "commune": _commune_from_address(item, zone_search),
        "zone_slug": zone_slug,
        "adr_eur": float(price),
        "occupancy_pct": _occupancy_proxy(rating, reviews),
        "capacity": item.get("personCapacity") or item.get("guests"),
        "type": item.get("roomType") or item.get("propertyType"),
        "amenities": [],
        "source": "Airbnb (Apify scrape)",
        "synthetic": False,
        "lat": float(lat),
        "lng": float(lng),
        "url": item.get("url"),
        "rating": float(rating) if isinstance(rating, (int, float)) else None,
        "review_count": int(reviews) if isinstance(reviews, (int, float)) else None,
    }


async def get_listings_for_zone(zone_slug: str) -> List[Dict[str, Any]]:
    """Return up to LIMIT_PER_ZONE comp listings for a zone.

    Cache → Apify → seed fallback, in that order. The route layer will
    flatten this with seed comps so the map always renders something.
    """
    cached = _read_cache(zone_slug)
    if cached:
        return cached

    if not apify_client.is_configured:
        return []

    search_term = ZONE_SEARCH_TERMS.get(zone_slug)
    if not search_term:
        return []

    actor_id = os.environ.get("APIFY_AIRBNB_ACTOR_ID", DEFAULT_ACTOR_ID)
    raw = await apify_client.run_actor_sync(
        actor_id,
        {
            "locationQueries": [search_term],
            "maxItems": LIMIT_PER_ZONE,
            "currency": "EUR",
        },
    )
    if not raw:
        return []

    comps: List[Dict[str, Any]] = []
    for item in raw[:LIMIT_PER_ZONE]:
        normalised = _normalise(item, zone_slug, search_term)
        if normalised:
            comps.append(normalised)

    if comps:
        _write_cache(zone_slug, comps)
    return comps


def seed_comps_for_zone(zone_slug: str) -> List[Dict[str, Any]]:
    """Thin wrapper so route handlers don't need to import the seeder."""
    return load_airbnb_comps(zone_slug)

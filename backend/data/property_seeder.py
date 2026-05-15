"""
Seed-data loaders. Read JSON files in data/seeds/ and serve them via
simple Python helpers so route handlers can pull seed corpora without
touching the filesystem on each request.

The DB seeder populates initial owners / properties / pipeline / etc.
on first startup so a fresh dashboard shows realistic content.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from database import db_session
from models.db_models import (
    DocumentCategory,
    LocationTag,
    MaintenanceStatus,
    Meeting,
    Milestone,
    MilestoneStatus,
    Owner,
    PipelineEntry,
    PipelineStatus,
    Property,
    Task,
    TaskStatus,
)


logger = logging.getLogger(__name__)

SEEDS_DIR = Path(__file__).parent / "seeds"


# ---------------------------------------------------------------
# JSON loaders (in-memory, idempotent)
# ---------------------------------------------------------------


def _load(filename: str) -> Any:
    path = SEEDS_DIR / filename
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_zones() -> List[Dict[str, Any]]:
    return _load("zones.json")


def load_communes() -> List[Dict[str, Any]]:
    return _load("communes.json")


def load_regulations() -> Dict[str, Any]:
    return _load("regulations.json")


def load_airbnb_comps(zone_slug: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _load("airbnb_comps.json")
    if zone_slug:
        rows = [r for r in rows if r.get("zone_slug") == zone_slug]
    return rows


def load_rental_comps(zone_slug: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _load("rental_comps.json")
    if zone_slug:
        rows = [r for r in rows if r.get("zone_slug") == zone_slug]
    return rows


def load_news_signals(zone_slug: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _load("news_signals.json")
    if zone_slug:
        rows = [r for r in rows if zone_slug in r.get("zone_relevance", [])]
    return rows


def load_monthly_str_series(zone_slug: Optional[str] = None) -> Dict[str, Any]:
    """24-month ADR + occupancy series. Returns the whole doc, or just the
    one zone's series list when zone_slug is given."""
    doc = _load("monthly_str_series.json")
    if zone_slug:
        return {
            "zone_slug": zone_slug,
            "as_of_month": doc.get("as_of_month"),
            "series": doc.get("series_by_zone", {}).get(zone_slug, []),
            "source": "seed (derived from 2026 medians + French seasonality)",
        }
    return doc


def load_dpe_distribution(code_insee: Optional[str] = None) -> Dict[str, Any]:
    """Per-commune DPE class shares. Whole doc, or one commune's record."""
    doc = _load("dpe_distribution.json")
    if code_insee:
        return doc.get("by_code_insee", {}).get(code_insee, {})
    return doc


# ---------------------------------------------------------------
# DB seeder — populates operational tables on first startup
# ---------------------------------------------------------------


def seed_operational_tables_if_empty() -> None:
    """Idempotent: only inserts rows if the table is empty."""
    with db_session() as db:
        if db.query(Owner).count() == 0:
            _seed_owners(db)
        if db.query(Milestone).count() == 0:
            _seed_milestones(db)
        if db.query(Meeting).count() == 0:
            _seed_meetings(db)


def _seed_owners(db) -> None:
    owners_data = [
        {"name": "Sophie Marchand", "email": "s.marchand@gmail.com", "phone": "+33 6 12 34 56 78",
         "source": "Cessy network", "notes": "Lives near Saint-Genis-Pouilly; owns 2 T2s in Ferney-Voltaire."},
        {"name": "Jean-Marc Dubois", "email": "jmdubois@laposte.net", "phone": "+33 6 78 90 12 34",
         "source": "LeBonCoin contact", "notes": "Open to long lease in Annecy outskirts."},
        {"name": "Élodie Roux", "email": "elodie.roux@orange.fr", "phone": "+33 6 45 67 89 01",
         "source": "Referral · Malmö contact", "notes": "Two properties in Lyon 7e and Villeurbanne; warm intro."},
        {"name": "Pierre Bertrand", "email": "pierre.bertrand@yahoo.fr", "phone": "+33 6 23 45 67 89",
         "source": "Cold outreach", "notes": "Owner of T3 in Grenoble centre; first contact April."},
        {"name": "Catherine Lefèvre", "email": "c.lefevre@free.fr", "phone": "+33 6 56 78 90 12",
         "source": "Local agent intro", "notes": "Multi-property owner in Dijon; potential portfolio deal."},
    ]
    for d in owners_data:
        db.add(Owner(**d))
    db.flush()

    properties = [
        {"owner_id": 1, "commune": "Ferney-Voltaire", "zone_slug": "pays-de-gex",
         "type": "T2", "size_m2": 48, "rooms": 2, "rent_monthly": 1180, "charges": 80, "dpe_class": "D"},
        {"owner_id": 1, "commune": "Ferney-Voltaire", "zone_slug": "pays-de-gex",
         "type": "T2", "size_m2": 52, "rooms": 2, "rent_monthly": 1240, "charges": 85, "dpe_class": "C"},
        {"owner_id": 2, "commune": "Sévrier", "zone_slug": "annecy-haute-savoie",
         "type": "T3", "size_m2": 64, "rooms": 3, "rent_monthly": 1180, "charges": 90, "dpe_class": "D"},
        {"owner_id": 3, "commune": "Lyon 7e", "zone_slug": "greater-lyon",
         "type": "T2", "size_m2": 46, "rooms": 2, "rent_monthly": 980, "charges": 75, "dpe_class": "E"},
        {"owner_id": 3, "commune": "Villeurbanne", "zone_slug": "greater-lyon",
         "type": "Studio", "size_m2": 28, "rooms": 1, "rent_monthly": 720, "charges": 55, "dpe_class": "D"},
        {"owner_id": 4, "commune": "Grenoble", "zone_slug": "grenoble-isere",
         "type": "T3", "size_m2": 62, "rooms": 3, "rent_monthly": 880, "charges": 70, "dpe_class": "D"},
        {"owner_id": 5, "commune": "Dijon", "zone_slug": "dijon-cote-dor",
         "type": "T2", "size_m2": 50, "rooms": 2, "rent_monthly": 720, "charges": 60, "dpe_class": "C"},
        {"owner_id": 5, "commune": "Dijon", "zone_slug": "dijon-cote-dor",
         "type": "T3", "size_m2": 70, "rooms": 3, "rent_monthly": 980, "charges": 85, "dpe_class": "D"},
    ]
    for p in properties:
        db.add(Property(**p))

    pipeline = [
        {"owner_id": 1, "status": PipelineStatus.NEGOTIATION, "notes": "Terms agreed on 1st T2; waiting on second.",
         "last_contact": date.today() - timedelta(days=3), "next_followup": date.today() + timedelta(days=4)},
        {"owner_id": 2, "status": PipelineStatus.CONTACT, "notes": "Initial call done; wants to see numbers.",
         "last_contact": date.today() - timedelta(days=7), "next_followup": date.today() + timedelta(days=2)},
        {"owner_id": 3, "status": PipelineStatus.SIGNED, "notes": "Both properties signed; activation underway.",
         "last_contact": date.today() - timedelta(days=12), "next_followup": date.today() + timedelta(days=14)},
        {"owner_id": 4, "status": PipelineStatus.LEAD, "notes": "Single property; needs warm-up.",
         "last_contact": date.today() - timedelta(days=21), "next_followup": date.today() + timedelta(days=1)},
        {"owner_id": 5, "status": PipelineStatus.CONTACT, "notes": "Portfolio play; second meeting scheduled.",
         "last_contact": date.today() - timedelta(days=5), "next_followup": date.today() + timedelta(days=10)},
    ]
    for p in pipeline:
        db.add(PipelineEntry(**p))
    logger.info("Seeded %d owners, %d properties, %d pipeline entries",
                len(owners_data), len(properties), len(pipeline))


def _seed_milestones(db) -> None:
    milestones = [
        {"title": "MVP scaffold deployed", "description": "Backend + frontend live on Render.",
         "target_date": date.today() - timedelta(days=5), "status": MilestoneStatus.COMPLETE},
        {"title": "First 3 properties activated", "description": "Sign + onboard 3 properties for active sub-let.",
         "target_date": date.today() + timedelta(days=21), "status": MilestoneStatus.IN_PROGRESS},
        {"title": "Annecy zone validation", "description": "Validate Annecy as priority-1 target with real comp data.",
         "target_date": date.today() + timedelta(days=35), "status": MilestoneStatus.IN_PROGRESS},
        {"title": "Cleaning ops contract", "description": "Establish cleaner agreements for Pays de Gex + Annecy.",
         "target_date": date.today() + timedelta(days=14), "status": MilestoneStatus.NOT_STARTED},
        {"title": "First quarterly P&L review", "description": "Q1 2026 financial review with Malmö team.",
         "target_date": date.today() + timedelta(days=70), "status": MilestoneStatus.NOT_STARTED},
    ]
    for m in milestones:
        db.add(Milestone(**m))
    db.flush()

    tasks = [
        {"milestone_id": 2, "title": "Send draft lease to Sophie Marchand", "assignee": "Cessy",
         "due_date": date.today() + timedelta(days=2), "status": TaskStatus.DOING},
        {"milestone_id": 2, "title": "Photograph Ferney-Voltaire T2", "assignee": "Cessy",
         "due_date": date.today() + timedelta(days=5), "status": TaskStatus.TODO},
        {"milestone_id": 3, "title": "Scrape Annecy lakeside Airbnb comps", "assignee": "Malmö",
         "due_date": date.today() + timedelta(days=4), "status": TaskStatus.DOING},
        {"milestone_id": 4, "title": "Get 3 cleaning quotes for Pays de Gex", "assignee": "Cessy",
         "due_date": date.today() + timedelta(days=7), "status": TaskStatus.TODO},
    ]
    for t in tasks:
        db.add(Task(**t))


def _seed_meetings(db) -> None:
    meetings = [
        {"title": "Malmö–Cessy weekly sync", "meeting_date": date.today() - timedelta(days=7),
         "location_tag": LocationTag.REMOTE, "attendees": ["Robert", "Thomas"],
         "notes_md": "## Agenda\n- Pipeline status\n- Property activation timeline\n- Operations setup",
         "action_items": [{"text": "Send Sophie's lease draft", "assignee": "Cessy", "due": str(date.today() + timedelta(days=2))}]},
        {"title": "First property walkthrough · Ferney-Voltaire", "meeting_date": date.today() - timedelta(days=3),
         "location_tag": LocationTag.CESSY, "attendees": ["Thomas", "Sophie Marchand"],
         "notes_md": "## Walkthrough notes\n- T2 in good shape\n- DPE class D — compliant for 2026\n- Owner agreed in principle\n- Need photos + furniture inventory",
         "action_items": [{"text": "Photograph apartment", "assignee": "Cessy", "due": str(date.today() + timedelta(days=5))}]},
    ]
    for m in meetings:
        db.add(Meeting(**m))

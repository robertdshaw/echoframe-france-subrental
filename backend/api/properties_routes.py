"""
Properties — flat list, CRUD, and the real-data scoring engine.

The "manual import + auto-score" workflow: the operator sources a flat
themselves (DataDome blocks scraping listings), enters it here, and the
scorer rates it against real market data — margin, spread vs official
rent, DPE ban exposure, regulatory friction, verdict, and the
back-solved landlord offer. /ranked sorts every entered flat best-first.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import AdhocScoreRequest, PropertyCreate, PropertyRead
from database import get_db
from models.db_models import Property
from services.property_scorer import rank_properties, score_property

router = APIRouter(prefix="/api/properties", tags=["properties"])


def _to_dict(p: Property) -> Dict[str, Any]:
    return {
        "id": p.id,
        "owner_id": p.owner_id,
        "commune": p.commune,
        "zone_slug": p.zone_slug,
        "address": p.address,
        "type": p.type,
        "size_m2": p.size_m2,
        "rooms": p.rooms,
        "rent_monthly": p.rent_monthly,
        "charges": p.charges,
        "dpe_class": p.dpe_class,
        "notes": p.notes,
    }


@router.get("", response_model=List[PropertyRead])
def list_properties(db: Session = Depends(get_db)) -> List[Property]:
    """Every property across all owners (the candidate pool)."""
    return db.query(Property).order_by(Property.id.desc()).all()


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: int, payload: PropertyCreate, db: Session = Depends(get_db)
) -> Property:
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(prop, k, v)
    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/{property_id}")
def delete_property(property_id: int, db: Session = Depends(get_db)) -> dict:
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    db.delete(prop)
    db.commit()
    return {"status": "deleted", "id": property_id}


@router.post("/score")
def score_adhoc(payload: AdhocScoreRequest) -> Dict[str, Any]:
    """Score a flat the operator sourced, WITHOUT saving it.

    This is the import-preview: paste address-less specs (commune,
    size, asking rent), see margin / spread / verdict / landlord offer
    on real market data before deciding to add it.
    """
    prop = payload.model_dump(exclude={"target_margin_pct"})
    return score_property(prop, target_margin_pct=payload.target_margin_pct)


@router.get("/{property_id}/score")
def score_saved(property_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return score_property(_to_dict(prop))


@router.get("/ranked")
def ranked(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """All entered properties, scored and ranked best-first."""
    props = [_to_dict(p) for p in db.query(Property).all()]
    scored = rank_properties(props)
    return {
        "n_properties": len(scored),
        "top_5": scored[:5],
        "all": scored,
    }

"""Owners + properties CRUD."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import OwnerCreate, OwnerRead, PropertyCreate, PropertyRead
from database import get_db
from models.db_models import Owner, Property

router = APIRouter(prefix="/api/owners", tags=["owners"])


@router.get("", response_model=List[OwnerRead])
def list_owners(db: Session = Depends(get_db)) -> List[Owner]:
    return db.query(Owner).order_by(Owner.created_at.desc()).all()


@router.post("", response_model=OwnerRead)
def create_owner(payload: OwnerCreate, db: Session = Depends(get_db)) -> Owner:
    owner = Owner(**payload.model_dump())
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


@router.get("/{owner_id}", response_model=OwnerRead)
def get_owner(owner_id: int, db: Session = Depends(get_db)) -> Owner:
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return owner


@router.patch("/{owner_id}", response_model=OwnerRead)
def update_owner(owner_id: int, payload: OwnerCreate, db: Session = Depends(get_db)) -> Owner:
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(owner, k, v)
    db.commit()
    db.refresh(owner)
    return owner


@router.delete("/{owner_id}")
def delete_owner(owner_id: int, db: Session = Depends(get_db)) -> dict:
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    db.delete(owner)
    db.commit()
    return {"status": "deleted", "id": owner_id}


@router.get("/{owner_id}/properties", response_model=List[PropertyRead])
def owner_properties(owner_id: int, db: Session = Depends(get_db)) -> List[Property]:
    return db.query(Property).filter(Property.owner_id == owner_id).all()


@router.post("/{owner_id}/properties", response_model=PropertyRead)
def create_property(owner_id: int, payload: PropertyCreate, db: Session = Depends(get_db)) -> Property:
    data = payload.model_dump()
    data["owner_id"] = owner_id
    prop = Property(**data)
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop

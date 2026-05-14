"""Owner pipeline kanban (Lead → Contact → Negotiation → Signed → Active)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import PipelineEntryCreate, PipelineEntryRead, PipelineStatusUpdate
from database import get_db
from models.db_models import PipelineEntry, PipelineStatus

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/owners", response_model=List[PipelineEntryRead])
def list_entries(db: Session = Depends(get_db)):
    return db.query(PipelineEntry).order_by(PipelineEntry.updated_at.desc()).all()


@router.post("/owners", response_model=PipelineEntryRead)
def create_entry(payload: PipelineEntryCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["status"] = PipelineStatus(data["status"])
    entry = PipelineEntry(**data)
    db.add(entry); db.commit(); db.refresh(entry)
    return entry


@router.patch("/owners/{entry_id}/status", response_model=PipelineEntryRead)
def update_status(entry_id: int, payload: PipelineStatusUpdate, db: Session = Depends(get_db)):
    entry = db.query(PipelineEntry).filter(PipelineEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found")
    entry.status = PipelineStatus(payload.status)
    if payload.notes is not None:
        entry.notes = payload.notes
    db.commit(); db.refresh(entry)
    return entry


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    counts = {s.value: 0 for s in PipelineStatus}
    for entry in db.query(PipelineEntry).all():
        counts[entry.status.value] += 1
    return {"counts_by_status": counts, "total": sum(counts.values())}

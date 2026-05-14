"""Meetings + cross-meeting action items."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import MeetingEntry
from database import get_db
from models.db_models import LocationTag, Meeting

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.get("", response_model=List[MeetingEntry])
def list_meetings(db: Session = Depends(get_db)):
    return db.query(Meeting).order_by(Meeting.meeting_date.desc()).all()


@router.post("", response_model=MeetingEntry)
def add_meeting(payload: MeetingEntry, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"id"})
    data["location_tag"] = LocationTag(data["location_tag"])
    item = Meeting(**data)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/{meeting_id}", response_model=MeetingEntry)
def update_meeting(meeting_id: int, payload: MeetingEntry, db: Session = Depends(get_db)):
    item = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Meeting not found")
    data = payload.model_dump(exclude_unset=True, exclude={"id"})
    if "location_tag" in data:
        data["location_tag"] = LocationTag(data["location_tag"])
    for k, v in data.items():
        setattr(item, k, v)
    db.commit(); db.refresh(item)
    return item


@router.get("/action-items")
def all_action_items(db: Session = Depends(get_db)):
    """Roll up action items across all meetings."""
    out = []
    for m in db.query(Meeting).all():
        for item in (m.action_items or []):
            out.append({**item, "meeting_id": m.id, "meeting_title": m.title, "meeting_date": m.meeting_date.isoformat()})
    return {"action_items": out, "count": len(out)}

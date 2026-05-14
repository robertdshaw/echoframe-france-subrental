"""Milestones + nested tasks (Gantt feed)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import MilestoneEntry, TaskEntry
from database import get_db
from models.db_models import Milestone, MilestoneStatus, Task

router = APIRouter(prefix="/api/milestones", tags=["milestones"])


@router.get("", response_model=List[MilestoneEntry])
def list_milestones(db: Session = Depends(get_db)):
    return db.query(Milestone).order_by(Milestone.target_date).all()


@router.post("", response_model=MilestoneEntry)
def add_milestone(payload: MilestoneEntry, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"id"})
    data["status"] = MilestoneStatus(data["status"])
    item = Milestone(**data)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/{milestone_id}", response_model=MilestoneEntry)
def update_milestone(milestone_id: int, payload: MilestoneEntry, db: Session = Depends(get_db)):
    item = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Milestone not found")
    data = payload.model_dump(exclude_unset=True, exclude={"id"})
    if "status" in data:
        data["status"] = MilestoneStatus(data["status"])
    for k, v in data.items():
        setattr(item, k, v)
    db.commit(); db.refresh(item)
    return item


@router.get("/{milestone_id}/tasks", response_model=List[TaskEntry])
def list_tasks(milestone_id: int, db: Session = Depends(get_db)):
    return db.query(Task).filter(Task.milestone_id == milestone_id).all()


@router.get("/timeline")
def timeline(db: Session = Depends(get_db)):
    """Gantt feed: milestone + nested task counts by status."""
    rows = []
    for m in db.query(Milestone).order_by(Milestone.target_date).all():
        n_tasks = db.query(Task).filter(Task.milestone_id == m.id).count()
        rows.append({
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "target_date": m.target_date.isoformat() if m.target_date else None,
            "status": m.status.value,
            "n_tasks": n_tasks,
        })
    return {"milestones": rows}

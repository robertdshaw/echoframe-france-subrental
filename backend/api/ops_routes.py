"""Cleaning schedule + maintenance tickets + operational tasks."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import CleaningEntry, MaintenanceTicketEntry, TaskEntry
from database import get_db
from models.db_models import CleaningSchedule, MaintenanceStatus, MaintenanceTicket, Task, TaskStatus

router = APIRouter(prefix="/api/ops", tags=["ops"])


# Cleaning ---------------------------------------------------------

@router.get("/cleaning", response_model=List[CleaningEntry])
def list_cleaning(db: Session = Depends(get_db)):
    return db.query(CleaningSchedule).order_by(CleaningSchedule.schedule_date).all()


@router.post("/cleaning", response_model=CleaningEntry)
def add_cleaning(payload: CleaningEntry, db: Session = Depends(get_db)):
    item = CleaningSchedule(**payload.model_dump(exclude={"id"}))
    db.add(item); db.commit(); db.refresh(item)
    return item


# Maintenance ------------------------------------------------------

@router.get("/maintenance", response_model=List[MaintenanceTicketEntry])
def list_maintenance(db: Session = Depends(get_db)):
    return db.query(MaintenanceTicket).order_by(MaintenanceTicket.created_at.desc()).all()


@router.post("/maintenance", response_model=MaintenanceTicketEntry)
def add_maintenance(payload: MaintenanceTicketEntry, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"id", "created_at", "resolved_at"})
    data["status"] = MaintenanceStatus(data["status"])
    item = MaintenanceTicket(**data)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/maintenance/{ticket_id}", response_model=MaintenanceTicketEntry)
def update_maintenance(ticket_id: int, payload: MaintenanceTicketEntry, db: Session = Depends(get_db)):
    item = db.query(MaintenanceTicket).filter(MaintenanceTicket.id == ticket_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ticket not found")
    data = payload.model_dump(exclude_unset=True, exclude={"id"})
    if "status" in data:
        data["status"] = MaintenanceStatus(data["status"])
    for k, v in data.items():
        setattr(item, k, v)
    db.commit(); db.refresh(item)
    return item


# Tasks ------------------------------------------------------------

@router.get("/tasks", response_model=List[TaskEntry])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.due_date).all()


@router.post("/tasks", response_model=TaskEntry)
def add_task(payload: TaskEntry, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"id"})
    data["status"] = TaskStatus(data["status"])
    item = Task(**data)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/tasks/{task_id}", response_model=TaskEntry)
def update_task(task_id: int, payload: TaskEntry, db: Session = Depends(get_db)):
    item = db.query(Task).filter(Task.id == task_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    data = payload.model_dump(exclude_unset=True, exclude={"id"})
    if "status" in data:
        data["status"] = TaskStatus(data["status"])
    for k, v in data.items():
        setattr(item, k, v)
    db.commit(); db.refresh(item)
    return item

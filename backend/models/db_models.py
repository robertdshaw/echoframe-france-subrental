"""
SQLAlchemy ORM models for EchoFrame France Subrental.

These cover the operational side of the dashboard — owners, pipeline,
properties, finance, ops, milestones, meetings, documents. The market-
intelligence pieces (forecasts, regime, narrative) flow through services
and never hit the DB.
"""

from __future__ import annotations

import enum
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ---------------------------------------------------------------
# Enums
# ---------------------------------------------------------------


class PipelineStatus(str, enum.Enum):
    LEAD = "lead"
    CONTACT = "contact"
    NEGOTIATION = "negotiation"
    SIGNED = "signed"
    ACTIVE = "active"
    LOST = "lost"


class MaintenanceStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    BLOCKED = "blocked"


class MilestoneStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AT_RISK = "at_risk"
    COMPLETE = "complete"


class LocationTag(str, enum.Enum):
    MALMO = "malmo"
    CESSY = "cessy"
    REMOTE = "remote"


class DocumentCategory(str, enum.Enum):
    CONTRACT = "contract"
    TEMPLATE = "template"
    LEGAL = "legal"
    COMPLIANCE = "compliance"
    OTHER = "other"


# ---------------------------------------------------------------
# Owners + properties
# ---------------------------------------------------------------


class Owner(Base):
    __tablename__ = "owners"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    source: Mapped[Optional[str]] = mapped_column(String(100), comment="Lead source")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    properties: Mapped[List["Property"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    pipeline_entries: Mapped[List["PipelineEntry"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id", ondelete="CASCADE"))
    commune: Mapped[str] = mapped_column(String(100))
    zone_slug: Mapped[Optional[str]] = mapped_column(String(80))
    address: Mapped[Optional[str]] = mapped_column(String(300))
    type: Mapped[Optional[str]] = mapped_column(String(50), comment="Studio / T1 / T2 / T3 / Maison")
    size_m2: Mapped[Optional[int]] = mapped_column(Integer)
    rooms: Mapped[Optional[int]] = mapped_column(Integer)
    rent_monthly: Mapped[Optional[float]] = mapped_column(Float)
    charges: Mapped[Optional[float]] = mapped_column(Float)
    dpe_class: Mapped[Optional[str]] = mapped_column(String(2))
    photos: Mapped[Optional[list]] = mapped_column(JSON)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    owner: Mapped["Owner"] = relationship(back_populates="properties")


# ---------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------


class PipelineEntry(Base):
    __tablename__ = "pipeline_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id", ondelete="CASCADE"))
    status: Mapped[PipelineStatus] = mapped_column(
        SAEnum(PipelineStatus), default=PipelineStatus.LEAD
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    last_contact: Mapped[Optional[date]] = mapped_column(Date)
    next_followup: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    owner: Mapped["Owner"] = relationship(back_populates="pipeline_entries")


# ---------------------------------------------------------------
# Finance
# ---------------------------------------------------------------


class Budget(Base):
    __tablename__ = "budget"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    period: Mapped[str] = mapped_column(String(20), comment="monthly / one-off / annual")
    notes: Mapped[Optional[str]] = mapped_column(Text)


class Revenue(Base):
    __tablename__ = "revenue"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[Optional[int]] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"))
    month: Mapped[date] = mapped_column(Date)
    gross_revenue: Mapped[float] = mapped_column(Float)
    platform_fees: Mapped[float] = mapped_column(Float, default=0.0)
    net_revenue: Mapped[float] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String(50), comment="Airbnb / Booking / direct")


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[Optional[int]] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"))
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    expense_date: Mapped[date] = mapped_column(Date)
    description: Mapped[Optional[str]] = mapped_column(Text)
    receipt_url: Mapped[Optional[str]] = mapped_column(String(500))


# ---------------------------------------------------------------
# Operations
# ---------------------------------------------------------------


class CleaningSchedule(Base):
    __tablename__ = "cleaning_schedule"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    schedule_date: Mapped[date] = mapped_column(Date)
    cleaner_name: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    notes: Mapped[Optional[str]] = mapped_column(Text)


class MaintenanceTicket(Base):
    __tablename__ = "maintenance_tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[MaintenanceStatus] = mapped_column(
        SAEnum(MaintenanceStatus), default=MaintenanceStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    milestone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("milestones.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[Optional[str]] = mapped_column(Text)
    assignee: Mapped[Optional[str]] = mapped_column(String(100))
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.TODO)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------
# Milestones / meetings / documents
# ---------------------------------------------------------------


class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[Optional[str]] = mapped_column(Text)
    target_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[MilestoneStatus] = mapped_column(
        SAEnum(MilestoneStatus), default=MilestoneStatus.NOT_STARTED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    meeting_date: Mapped[date] = mapped_column(Date)
    location_tag: Mapped[LocationTag] = mapped_column(
        SAEnum(LocationTag), default=LocationTag.REMOTE
    )
    attendees: Mapped[Optional[list]] = mapped_column(JSON)
    notes_md: Mapped[Optional[str]] = mapped_column(Text)
    action_items: Mapped[Optional[list]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[DocumentCategory] = mapped_column(
        SAEnum(DocumentCategory), default=DocumentCategory.OTHER
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

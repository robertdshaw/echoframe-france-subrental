"""Pydantic v2 request / response schemas for EchoFrame France."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------
# Market intelligence
# ---------------------------------------------------------------


class ZoneSummary(BaseModel):
    slug: str
    name: str
    profile: str
    communes: List[str]
    center: List[float]
    radius_km: float
    median_adr_eur: float
    median_rent_per_m2_eur: float
    median_occupancy_pct: float
    regulatory_friction: str
    expected_net_margin_eur: Optional[float] = None
    expected_net_margin_pct: Optional[float] = None
    verdict: Optional[str] = Field(None, description="TARGET / WAIT / AVOID")


class CommuneSummary(BaseModel):
    name: str
    zone_slug: str
    code_insee: str
    lat: float
    lng: float
    population: int
    median_income_eur: float
    vacancy_rate_pct: float
    active_workers: Optional[int] = None


class CompListing(BaseModel):
    id: str
    commune: str
    zone_slug: str
    adr_eur: Optional[float] = None
    occupancy_pct: Optional[float] = None
    capacity: Optional[int] = None
    rent_monthly: Optional[float] = None
    charges: Optional[float] = None
    size_m2: Optional[float] = None
    rooms: Optional[int] = None
    type: Optional[str] = None
    amenities: Optional[List[str]] = None
    source: str
    synthetic: bool = False
    # Populated for scraped listings (Apify). Frontend prefers these over
    # commune-centroid fallback when present.
    lat: Optional[float] = None
    lng: Optional[float] = None
    url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None


class ConfidenceInterval(BaseModel):
    lower: float
    upper: float
    confidence_level: int


class HorizonForecast(BaseModel):
    horizon_months: int
    median_change_pct: float
    ci_80: ConfidenceInterval
    ci_95: ConfidenceInterval
    p_positive: float


class ZoneForecastResponse(BaseModel):
    zone: ZoneSummary
    forecasts: List[HorizonForecast]
    current_regime: str
    regime_confidence: float
    timestamp: datetime


class WaterfallLineSchema(BaseModel):
    key: str
    label: str
    value_eur: float
    note: str = ""
    source: str = ""


class MarginRequest(BaseModel):
    adr_eur: float
    occupancy_pct: float
    rent_monthly_eur: float
    capacity: int = 4
    charges_monthly_eur: float = 0.0
    platform_commission_pct: float = 3.0
    tax_regime: str = "micro_bic"
    classification: str = "non_classe"
    tmi_pct: float = 30.0


class MarginResponse(BaseModel):
    gross_revenue_annual_eur: float
    net_revenue_annual_eur: float
    landlord_costs_annual_eur: float
    operating_costs_annual_eur: float
    taxable_base_eur: float
    tax_eur: float
    net_margin_annual_eur: float
    net_margin_pct_of_revenue: float
    waterfall: List[WaterfallLineSchema]
    regime_used: str
    notes: List[str] = []


class TriggerState(BaseModel):
    key: str
    name: str
    status: str
    score: float
    observed: str
    threshold: str
    source: str


class EntryQualityResponse(BaseModel):
    zone_slug: str
    score_out_of_10: float
    verdict: str
    triggers: List[TriggerState]
    historical_analogy_period: Optional[str] = None
    historical_analogy_outcome_pct: Optional[float] = None


class HurdleRateRow(BaseModel):
    key: str
    label: str
    value_pct: float
    risk: str
    note: str
    highlight: bool = False


class ScenarioRow(BaseModel):
    key: str
    label: str
    probability: float
    median_pct: float
    band_lower_pct: float
    band_upper_pct: float
    description: str
    analogue: Optional[str] = None


class NarrativeResponse(BaseModel):
    status: str
    narrative: Optional[str] = None
    model: Optional[str] = None
    reason: Optional[str] = None
    generated_at: Optional[str] = None


class SignalResponse(BaseModel):
    id: str
    headline: str
    source: str
    date: str
    impact_score: float
    zone_relevance: List[str]
    category: str
    keywords: List[str] = []
    section_influence: Optional[str] = None
    confidence: str = "MODERATE"


# ---------------------------------------------------------------
# Operational CRUD
# ---------------------------------------------------------------


class AdhocScoreRequest(BaseModel):
    """Score a flat the operator sourced manually, without saving it."""
    commune: str
    size_m2: float
    rent_monthly: float
    type: Optional[str] = None
    rooms: Optional[int] = None
    capacity: Optional[int] = None
    charges: Optional[float] = None
    dpe_class: Optional[str] = None
    zone_slug: Optional[str] = None
    target_margin_pct: float = 18.0


class OwnerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class OwnerRead(OwnerCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class PropertyCreate(BaseModel):
    owner_id: int
    commune: str
    zone_slug: Optional[str] = None
    address: Optional[str] = None
    type: Optional[str] = None
    size_m2: Optional[int] = None
    rooms: Optional[int] = None
    rent_monthly: Optional[float] = None
    charges: Optional[float] = None
    dpe_class: Optional[str] = None
    notes: Optional[str] = None


class PropertyRead(PropertyCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


class PipelineEntryCreate(BaseModel):
    owner_id: int
    status: str = "lead"
    notes: Optional[str] = None
    last_contact: Optional[date] = None
    next_followup: Optional[date] = None


class PipelineEntryRead(PipelineEntryCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class PipelineStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class BudgetEntry(BaseModel):
    id: Optional[int] = None
    category: str
    amount: float
    period: str
    notes: Optional[str] = None
    model_config = {"from_attributes": True}


class RevenueEntry(BaseModel):
    id: Optional[int] = None
    property_id: Optional[int] = None
    month: date
    gross_revenue: float
    platform_fees: float = 0.0
    net_revenue: float
    source: Optional[str] = None
    model_config = {"from_attributes": True}


class ExpenseEntry(BaseModel):
    id: Optional[int] = None
    property_id: Optional[int] = None
    category: str
    amount: float
    expense_date: date
    description: Optional[str] = None
    receipt_url: Optional[str] = None
    model_config = {"from_attributes": True}


class CleaningEntry(BaseModel):
    id: Optional[int] = None
    property_id: int
    schedule_date: date
    cleaner_name: Optional[str] = None
    status: str = "scheduled"
    notes: Optional[str] = None
    model_config = {"from_attributes": True}


class MaintenanceTicketEntry(BaseModel):
    id: Optional[int] = None
    property_id: int
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "open"
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class TaskEntry(BaseModel):
    id: Optional[int] = None
    milestone_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    status: str = "todo"
    model_config = {"from_attributes": True}


class MilestoneEntry(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    target_date: Optional[date] = None
    status: str = "not_started"
    model_config = {"from_attributes": True}


class MeetingEntry(BaseModel):
    id: Optional[int] = None
    title: str
    meeting_date: date
    location_tag: str = "remote"
    attendees: Optional[List[str]] = None
    notes_md: Optional[str] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    model_config = {"from_attributes": True}


class DocumentEntry(BaseModel):
    id: Optional[int] = None
    title: str
    category: str = "other"
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    notes: Optional[str] = None
    model_config = {"from_attributes": True}

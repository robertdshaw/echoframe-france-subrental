"""Finance: budget / revenue / expense / aggregate P&L."""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.schemas import BudgetEntry, ExpenseEntry, RevenueEntry
from database import get_db
from models.db_models import Budget, Expense, Revenue

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.get("/budget", response_model=List[BudgetEntry])
def list_budget(db: Session = Depends(get_db)):
    return db.query(Budget).all()


@router.post("/budget", response_model=BudgetEntry)
def add_budget(payload: BudgetEntry, db: Session = Depends(get_db)):
    item = Budget(**payload.model_dump(exclude={"id"}))
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.get("/revenue", response_model=List[RevenueEntry])
def list_revenue(db: Session = Depends(get_db)):
    return db.query(Revenue).order_by(Revenue.month.desc()).all()


@router.post("/revenue", response_model=RevenueEntry)
def add_revenue(payload: RevenueEntry, db: Session = Depends(get_db)):
    item = Revenue(**payload.model_dump(exclude={"id"}))
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.get("/expenses", response_model=List[ExpenseEntry])
def list_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).order_by(Expense.expense_date.desc()).all()


@router.post("/expenses", response_model=ExpenseEntry)
def add_expense(payload: ExpenseEntry, db: Session = Depends(get_db)):
    item = Expense(**payload.model_dump(exclude={"id"}))
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.get("/pnl")
def pnl_statement(
    period: str = Query("monthly", description="monthly | quarterly | ytd"),
    db: Session = Depends(get_db),
):
    """Roll up revenue + expenses by period."""
    revenues = db.query(Revenue).all()
    expenses = db.query(Expense).all()
    total_revenue = sum(r.net_revenue for r in revenues)
    total_expense = sum(e.amount for e in expenses)
    net = total_revenue - total_expense
    by_month: dict = {}
    for r in revenues:
        key = r.month.strftime("%Y-%m")
        by_month.setdefault(key, {"revenue": 0.0, "expense": 0.0})
        by_month[key]["revenue"] += r.net_revenue
    for e in expenses:
        key = e.expense_date.strftime("%Y-%m")
        by_month.setdefault(key, {"revenue": 0.0, "expense": 0.0})
        by_month[key]["expense"] += e.amount
    rows = sorted(
        [{"month": k, **v, "net": round(v["revenue"] - v["expense"], 2)} for k, v in by_month.items()],
        key=lambda r: r["month"],
    )
    return {
        "totals": {"revenue": round(total_revenue, 2), "expense": round(total_expense, 2), "net": round(net, 2)},
        "by_month": rows,
        "period": period,
    }


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    """Top-of-page card data."""
    total_budget = db.query(func.sum(Budget.amount)).scalar() or 0
    total_revenue = db.query(func.sum(Revenue.net_revenue)).scalar() or 0
    total_expense = db.query(func.sum(Expense.amount)).scalar() or 0
    return {
        "budget_total_eur": round(total_budget, 2),
        "revenue_ytd_eur": round(total_revenue, 2),
        "expense_ytd_eur": round(total_expense, 2),
        "net_ytd_eur": round(total_revenue - total_expense, 2),
    }

"""
French sub-rental margin calculator.

Given Airbnb side (ADR, occupancy, capacity) and landlord side
(rent, charges) for a parcel under sub-let, computes the full
cost stack and produces an itemised waterfall plus the net annual
USD-equivalent margin.

Cost ordering follows the French operator convention so the
waterfall reads naturally for an investor: gross revenue at the top,
each cost line as a drag, net margin at the bottom.

All inputs / outputs in EUR. Tax treatment toggles between
*micro-BIC* (50% abattement, default) and *réel simplifié*. The
réel path supports furniture amortisation when the operator is
LMNP/LMP. Operators above the micro-BIC threshold
(€77,700 from 2026) are forced into réel.

Numbers below are Q1 2026 French defaults; each line documents the
official source so the dashboard can render provenance tags.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


# ---------------------------------------------------------------
# Q1 2026 French defaults — documented sources in comments
# ---------------------------------------------------------------

# Airbnb host-side platform commission. 3% for "host-only" tier (host
# pays all); ~14-16% effective when the guest service fee is split.
# Default to 3% for cleanest math; bump in the UI if the operator uses
# the split-fee model.
PLATFORM_COMMISSION_PCT_DEFAULT = 3.0

# Cleaning per turnover. Operator-set in practice; €40-€80 typical
# (T1/Studio cheaper, family-size larger). Charged to guest in most
# operations; for net-to-host accounting we treat it as pass-through
# and exclude it. The dashboard surfaces it as a separate row at zero
# net impact so the cost stack stays interpretable.
CLEANING_PER_TURNOVER_EUR_DEFAULT = 60.0

# Linen + consumables (toilet paper, coffee, welcome basket, etc.).
# Industry default ~€8-€15 per stay. We treat this as a real cost.
LINEN_PER_TURNOVER_EUR_DEFAULT = 12.0

# Assurance Propriétaire Non Occupant (PNO) — typical 0.8-1.5% of
# annual rent for sub-let furnished. We use 1.2% as the mid-point.
ASSURANCE_PNO_PCT_OF_RENT_DEFAULT = 1.2

# Cotisation Foncière des Entreprises (CFE). Minimum €224/year for
# small CA; can reach ~€7,349 for top bands. €450 is a reasonable
# default for a single-parcel sub-let operator.
CFE_DEFAULT_EUR = 450.0

# Taxe de séjour — varies €0.20 to €4.65 per night per adult. €1.50
# is a typical mid-tier for furnished tourist accommodation in
# Rhône-Alpes / Bourgogne. Hosts collect from guests and remit; for
# net-to-host accounting this is pass-through but it limits ADR.
# We exclude from cost stack; the ADR already nets it implicitly.

# Furniture amortisation (réel only). Operators amortise over
# 5-10 years (mobilier) and 25-30 years (gros oeuvre). €1,500-€3,000
# annual amortisation is typical for a single furnished sub-let.
FURNITURE_AMORTISATION_DEFAULT_EUR = 2200.0

# Accountant fees (réel only). €600-€1,200/yr per parcel for a basic
# LMNP file. Micro-BIC operators usually self-file and skip this.
COMPTABLE_FEES_EUR_DEFAULT = 850.0

# Wi-Fi + utilities overage above what's bundled in rent + charges.
# Most leases for sub-let purposes set utilities-included with a
# clause for overages. €30/month average covers fibre + electricity
# tip-over.
UTILITIES_OVERAGE_MONTHLY_EUR_DEFAULT = 30.0

# Micro-BIC threshold and abattement. From 2026:
#   - Meublé classé classique: 71% abattement, threshold €15,000
#   - Meublé non classé: 50% abattement, threshold €77,700
# The dashboard defaults to non-classé. Set the operator to "classé"
# in the UI to flip both numbers.
MICRO_BIC_ABATTEMENT_NON_CLASSE = 0.50
MICRO_BIC_THRESHOLD_NON_CLASSE_EUR = 77_700.0
MICRO_BIC_ABATTEMENT_CLASSE = 0.71
MICRO_BIC_THRESHOLD_CLASSE_EUR = 15_000.0

# French income-tax marginal rate to apply on the taxable base.
# Default to 30% (the modal band for sub-rental operators); the UI
# slider lets investors set their personal TMI between 11% and 45%.
DEFAULT_TMI_PCT = 30.0

# Prélèvements sociaux on furnished rental income — 17.2% on LMNP,
# CSG/CRDS path. Adds to TMI for total marginal load.
PRELEVEMENTS_SOCIAUX_PCT = 17.2


# ---------------------------------------------------------------
# Types
# ---------------------------------------------------------------


TaxRegime = Literal["micro_bic", "reel_simplifie"]
ClassificationFr = Literal["non_classe", "classe"]


@dataclass(frozen=True)
class MarginInputs:
    """All inputs the calculator needs. EUR currency throughout."""
    adr_eur: float
    occupancy_pct: float                     # 0..100
    capacity: int
    rent_monthly_eur: float                  # what we pay landlord
    charges_monthly_eur: float = 0.0
    platform_commission_pct: float = PLATFORM_COMMISSION_PCT_DEFAULT
    cleaning_per_turnover_eur: float = CLEANING_PER_TURNOVER_EUR_DEFAULT
    avg_stay_nights: float = 3.0             # France-wide median ~3.0
    linen_per_turnover_eur: float = LINEN_PER_TURNOVER_EUR_DEFAULT
    assurance_pno_pct_of_rent: float = ASSURANCE_PNO_PCT_OF_RENT_DEFAULT
    cfe_eur: float = CFE_DEFAULT_EUR
    furniture_amortisation_eur: float = FURNITURE_AMORTISATION_DEFAULT_EUR
    comptable_fees_eur: float = COMPTABLE_FEES_EUR_DEFAULT
    utilities_overage_monthly_eur: float = UTILITIES_OVERAGE_MONTHLY_EUR_DEFAULT
    tax_regime: TaxRegime = "micro_bic"
    classification: ClassificationFr = "non_classe"
    tmi_pct: float = DEFAULT_TMI_PCT


@dataclass(frozen=True)
class WaterfallLine:
    """A single row in the margin waterfall."""
    key: str
    label: str
    value_eur: float                 # signed: positive = revenue, negative = cost
    note: str = ""
    source: str = ""


@dataclass(frozen=True)
class MarginResult:
    """Full output of the calculator."""
    gross_revenue_annual_eur: float
    net_revenue_annual_eur: float          # post-platform + cleaning passthrough
    landlord_costs_annual_eur: float       # rent + charges
    operating_costs_annual_eur: float      # insurance + CFE + utilities + cleaning + linen + accountant + amortisation
    taxable_base_eur: float
    tax_eur: float
    net_margin_annual_eur: float
    net_margin_pct_of_revenue: float
    waterfall: List[WaterfallLine]
    inputs: MarginInputs
    regime_used: TaxRegime
    notes: List[str]


# ---------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------


def compute_margin(inputs: MarginInputs) -> MarginResult:
    """Run the full margin computation; returns the waterfall + totals.

    The implementation is deliberately verbose — every line is a
    separately auditable cost so the waterfall can render each one as
    a row with its own source tag. Avoid the temptation to roll up.
    """
    notes: List[str] = []

    # ---- Revenue side -------------------------------------------
    occ_decimal = max(0.0, min(1.0, inputs.occupancy_pct / 100.0))
    booked_nights_year = 365 * occ_decimal
    gross_revenue = inputs.adr_eur * booked_nights_year

    # Platform commission (host-only tier default: 3%).
    platform_fee = -gross_revenue * (inputs.platform_commission_pct / 100.0)

    # Cleaning + linen: turnover count = booked_nights / avg_stay_nights.
    turnovers = booked_nights_year / max(1.0, inputs.avg_stay_nights)
    cleaning_total = -inputs.cleaning_per_turnover_eur * turnovers
    linen_total = -inputs.linen_per_turnover_eur * turnovers
    # Cleaning is typically charged to the guest as a separate fee;
    # treat it as a pass-through "in-and-out" for the operator. We
    # surface it in the waterfall at the absolute value so the cost
    # of doing business is visible, then add the pass-through revenue.
    cleaning_passthrough = -cleaning_total  # equal-and-opposite

    # ---- Landlord side -----------------------------------------
    rent_annual = -inputs.rent_monthly_eur * 12
    charges_annual = -inputs.charges_monthly_eur * 12

    # ---- Operating costs ----------------------------------------
    pno_insurance = -(inputs.assurance_pno_pct_of_rent / 100.0) * (inputs.rent_monthly_eur * 12)
    cfe = -inputs.cfe_eur
    utilities_overage = -inputs.utilities_overage_monthly_eur * 12
    # Furniture amortisation only deductible in réel.
    furniture = (
        -inputs.furniture_amortisation_eur
        if inputs.tax_regime == "reel_simplifie"
        else 0.0
    )
    comptable = (
        -inputs.comptable_fees_eur if inputs.tax_regime == "reel_simplifie" else 0.0
    )

    # ---- Pre-tax operating margin -------------------------------
    operating_revenue = gross_revenue + platform_fee + cleaning_passthrough
    operating_costs = (
        cleaning_total
        + linen_total
        + rent_annual
        + charges_annual
        + pno_insurance
        + cfe
        + utilities_overage
        + furniture
        + comptable
    )
    pre_tax_margin = operating_revenue + operating_costs

    # ---- Tax ----------------------------------------------------
    # micro-BIC: taxable base = (1 - abattement) × CA brut.
    # réel simplifié: taxable base = revenue − all deductible costs
    # (including amortisation + accountant fees).
    regime = inputs.tax_regime
    if regime == "micro_bic":
        abattement = (
            MICRO_BIC_ABATTEMENT_CLASSE
            if inputs.classification == "classe"
            else MICRO_BIC_ABATTEMENT_NON_CLASSE
        )
        threshold = (
            MICRO_BIC_THRESHOLD_CLASSE_EUR
            if inputs.classification == "classe"
            else MICRO_BIC_THRESHOLD_NON_CLASSE_EUR
        )
        if gross_revenue > threshold:
            notes.append(
                f"Gross revenue €{gross_revenue:,.0f} exceeds micro-BIC threshold "
                f"€{threshold:,.0f}; régime réel applied automatically."
            )
            regime = "reel_simplifie"
        else:
            taxable_base = gross_revenue * (1 - abattement)
    if regime == "reel_simplifie":
        # All operating costs already deducted in pre_tax_margin. Add
        # back rent + charges + pass-through cleaning so the taxable
        # base is gross_revenue − deductible_costs.
        # In practice TVA on furnished short-term is exempt below the
        # threshold; we ignore TVA here.
        taxable_base = max(0.0, pre_tax_margin)

    total_marginal_load_pct = inputs.tmi_pct + PRELEVEMENTS_SOCIAUX_PCT
    tax = taxable_base * (total_marginal_load_pct / 100.0)

    net_margin = pre_tax_margin - tax
    net_margin_pct = (
        100.0 * net_margin / gross_revenue if gross_revenue > 0 else 0.0
    )

    # ---- Waterfall lines (display order) -----------------------
    waterfall: List[WaterfallLine] = [
        WaterfallLine(
            key="gross_revenue",
            label="Gross revenue (ADR × booked nights)",
            value_eur=gross_revenue,
            note=f"{inputs.adr_eur:.0f}€/night × {booked_nights_year:.0f} nights",
            source="Airbnb comp scrape / forecast",
        ),
        WaterfallLine(
            key="cleaning_passthrough",
            label="+ Cleaning fee (guest-paid pass-through)",
            value_eur=cleaning_passthrough,
            note=f"{turnovers:.0f} turnovers × {inputs.cleaning_per_turnover_eur:.0f}€",
            source="Operator convention · guest fee",
        ),
        WaterfallLine(
            key="platform_fee",
            label="− Platform commission (host-only)",
            value_eur=platform_fee,
            note=f"{inputs.platform_commission_pct:.1f}% of gross",
            source="Airbnb host-only tier",
        ),
        WaterfallLine(
            key="cleaning_cost",
            label="− Cleaning ops",
            value_eur=cleaning_total,
            note=f"{turnovers:.0f} turnovers × {inputs.cleaning_per_turnover_eur:.0f}€",
            source="Cleaner contract",
        ),
        WaterfallLine(
            key="linen",
            label="− Linen & consumables",
            value_eur=linen_total,
            note=f"{turnovers:.0f} turnovers × {inputs.linen_per_turnover_eur:.0f}€",
            source="Industry default",
        ),
        WaterfallLine(
            key="rent",
            label="− Landlord rent (12 months)",
            value_eur=rent_annual,
            note=f"€{inputs.rent_monthly_eur:.0f}/mo × 12",
            source="Lease",
        ),
        WaterfallLine(
            key="charges",
            label="− Landlord charges locatives",
            value_eur=charges_annual,
            note=f"€{inputs.charges_monthly_eur:.0f}/mo × 12",
            source="Lease",
        ),
        WaterfallLine(
            key="pno_insurance",
            label="− Assurance PNO",
            value_eur=pno_insurance,
            note=f"{inputs.assurance_pno_pct_of_rent:.1f}% of annual rent",
            source="Insurance market default",
        ),
        WaterfallLine(
            key="cfe",
            label="− CFE (Cotisation Foncière des Entreprises)",
            value_eur=cfe,
            note="Single-parcel sub-let, mid-band",
            source="Code général des impôts art. 1447",
        ),
        WaterfallLine(
            key="utilities_overage",
            label="− Utilities + Wi-Fi overage",
            value_eur=utilities_overage,
            note=f"€{inputs.utilities_overage_monthly_eur:.0f}/mo × 12",
            source="Operator default",
        ),
    ]
    if regime == "reel_simplifie":
        waterfall.append(
            WaterfallLine(
                key="furniture_amortisation",
                label="− Furniture amortisation (LMNP)",
                value_eur=furniture,
                note="5-10y amortisation period",
                source="Régime réel · BIC",
            )
        )
        waterfall.append(
            WaterfallLine(
                key="comptable",
                label="− Accountant fees",
                value_eur=comptable,
                note="LMNP réel filing",
                source="Operator default",
            )
        )

    # Tax row
    regime_label = "Micro-BIC" if regime == "micro_bic" else "Régime réel simplifié"
    waterfall.append(
        WaterfallLine(
            key="tax",
            label=f"− Tax ({regime_label} · TMI {inputs.tmi_pct:.0f}% + PS 17.2%)",
            value_eur=-tax,
            note=f"Taxable base €{taxable_base:,.0f}",
            source="Code général des impôts",
        )
    )
    waterfall.append(
        WaterfallLine(
            key="net_margin",
            label="= Net annual margin (€)",
            value_eur=net_margin,
            note=f"{net_margin_pct:+.1f}% of gross revenue",
            source="Computed",
        )
    )

    return MarginResult(
        gross_revenue_annual_eur=round(gross_revenue, 2),
        net_revenue_annual_eur=round(gross_revenue + platform_fee + cleaning_passthrough, 2),
        landlord_costs_annual_eur=round(-(rent_annual + charges_annual), 2),
        operating_costs_annual_eur=round(
            -(cleaning_total + linen_total + pno_insurance + cfe + utilities_overage + furniture + comptable), 2
        ),
        taxable_base_eur=round(taxable_base, 2),
        tax_eur=round(tax, 2),
        net_margin_annual_eur=round(net_margin, 2),
        net_margin_pct_of_revenue=round(net_margin_pct, 2),
        waterfall=waterfall,
        inputs=inputs,
        regime_used=regime,
        notes=notes,
    )


def quick_margin_estimate(
    adr_eur: float,
    occupancy_pct: float,
    rent_monthly_eur: float,
    capacity: int = 4,
) -> Dict[str, float]:
    """Lightweight wrapper for the executive card. Returns just the net margin + key totals."""
    result = compute_margin(
        MarginInputs(
            adr_eur=adr_eur,
            occupancy_pct=occupancy_pct,
            capacity=capacity,
            rent_monthly_eur=rent_monthly_eur,
        )
    )
    return {
        "gross_revenue_eur": result.gross_revenue_annual_eur,
        "net_margin_eur": result.net_margin_annual_eur,
        "net_margin_pct": result.net_margin_pct_of_revenue,
        "regime_used": result.regime_used,
    }

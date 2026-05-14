# EchoFrame · France Subrental Intelligence

A narrative-first probabilistic forecasting dashboard for Airbnb sub-rental
arbitrage across a 150 km radius from Cessy — covering Pays de Gex,
Greater Lyon, Annecy & Haute-Savoie, Grenoble & Isère, Dijon &
Côte-d'Or, ski-access communes, and the Geneva periphery (FR side).

This is the operational workspace for the Malmö ↔ Cessy team:
market intelligence, owner pipeline, finance, ops, milestones,
meetings, and documents — all in one place. Sibling to the Argentina
real-estate dashboard; same anti-hallucination philosophy.

```
┌─────────────────────────────────────────────────────────────┐
│  THE CALL                                                   │
│  Each zone card: 12-mo net margin · TARGET / WAIT / AVOID  │
├─────────────────────────────────────────────────────────────┤
│  §01  Where to source        ─ comp spread by commune       │
│  §02  When to act            ─ 4 entry-quality triggers     │
│  §03  What you'll earn       ─ French cost-stack waterfall  │
│  §04  Versus alternatives    ─ Livret A / SCPI / direct     │
│  §05  Geography              ─ Airbnb + landlord maps       │
│  §06  Signals                ─ regulation + news feed       │
│  ▸  Evidence drawer (collapsed): trajectory, scenarios,    │
│     HMM regime, calibration backtest                        │
└─────────────────────────────────────────────────────────────┘
```

Plus operational sections: Pipeline · Owners · Finance · Operations ·
Milestones · Meetings · Documents.

---

## Architecture

```
echoframe-france-subrental/
├── backend/                       FastAPI · Python 3.11 · SQLAlchemy
│   ├── main.py                    App entry, lifespan prefetch, CORS
│   ├── config.py                  Settings + env validation
│   ├── database.py                SQLite for MVP, Postgres-ready
│   ├── api/                       11 routers (forecast / market /
│   │                              owners / pipeline / finance / ops /
│   │                              milestones / meetings / documents /
│   │                              signals / narrative)
│   ├── models/db_models.py        12 ORM tables
│   ├── services/
│   │   ├── margin_calculator.py   Full French cost-stack engine
│   │   └── forecast_service.py    Task-coalescing forecast cache
│   └── data/seeds/                Zones, communes, comps, regs, news
│
├── frontend/                      React 18 · Vite · TypeScript · Tailwind
│   └── src/
│       ├── App.tsx                10 routes
│       ├── pages/                 10 page components
│       ├── components/forecast/   ExecutiveCard ("THE CALL")
│       ├── components/layout/     Sidebar (9 sections)
│       └── api/client.ts          Axios + typed API helpers
│
├── render.yaml                    Render Blueprint (backend + static)
└── CLAUDE.md                      Build plan + remaining phases
```

---

## What ships in this commit (Phase 1 + Phase 2 core)

**Backend, runnable end-to-end:**
- 7 zones loaded from seed (Pays de Gex, Annecy, Lyon, Grenoble, Dijon,
  ski-access, Geneva periphery), 38 communes, 27 Airbnb comps, 18
  rental comps, 15 French-language news signals, per-commune
  regulatory status
- Full **French margin calculator** with the cost-stack waterfall:
  platform commission (host-only 3%), cleaning + linen, PNO insurance,
  CFE, taxe de séjour pass-through, landlord rent + charges, furniture
  amortisation, accountant fees, utilities overage. Micro-BIC vs Régime
  réel simplifié; classé vs non-classé classification. Income tax + PS
  applied on the taxable base
- Zone forecast service with 6/12/24-month posteriors, verdict heuristic
  (TARGET / WAIT / AVOID) keyed to net margin + regulatory friction
- Spread analyser: per-commune Airbnb-annual minus landlord-annual
- 11 routers, all CRUD-wired against SQLite
- Deterministic narrative briefing (5 paragraphs, slot-filled in Python)

**Frontend, runnable end-to-end:**
- 10 routes with sidebar nav (Dashboard / Market / Pipeline / Owners /
  Finance / Operations / Milestones / Meetings / Documents)
- Dashboard renders THE CALL — one ExecutiveCard per zone, sorted by
  net margin, with verdict pill and key stats
- Market Research page: cross-zone ranked table
- Zone Detail page: stats header, narrative briefing, spread table,
  6/12/24-month posteriors, signals feed
- Operational pages all fetch real data: Pipeline kanban, Owners table,
  Finance P&L, Ops three-column board, Milestones timeline, Meetings
  with action items, Documents library

**Deploy:**
- `render.yaml` Blueprint provisions backend (Frankfurt region) + static
  frontend in one go
- CORS locked to Render static-site origin + localhost ports with
  wildcard-credentials safety guard
- HTTP `Cache-Control` middleware on read-only GETs

---

## Deferred to follow-up sessions

These are stubbed or absent in this commit and scoped in `CLAUDE.md`:

- **Phase 2 model depth** — hierarchical Bayesian zone + commune
  models, HMM seasonality detector, Prospect Theory overlay, ensemble
  forecaster. Current implementation is a parametric Student-t around
  the margin-calculator output, which is directionally correct.
- **Phase 4 French NLP pipeline** — domestic-token allowlist filter +
  Haiku dual-scoring + cost ledger. Signals currently flow through a
  category→section heuristic.
- **Phase 5 maps + Recharts polish** — `AirbnbCompMap`,
  `LandlordZoneMap`, `SpreadHeatmap`, `MarginWaterfall` recharts
  component, `FanChart`, `SeasonalityStrip`. The spread data and
  waterfall data both ship through the API; only the rendering layer
  is pending.
- **Phase 6 Evidence drawer** — collapsible model-detail panel with
  HMM diagnostics, calibration backtest, three-scenario tail risk.
- **Phase 7 live data clients** — INSEE / Banque de France / Airbnb
  scraper / SeLoger scraper / DPE-register reader. All fallback to
  seeds without API keys.
- **LLM narrative polish** — deterministic draft serves now; Claude
  Sonnet polish is one method call away once `services/narrative_service.py`
  lands (pattern is the same as Argentina's).

---

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate                       # Windows
# source .venv/bin/activate                  # POSIX
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The SQLite database is created on first boot at `backend/echoframe_france.db`
and the operational seed loads automatically (5 owners, 8 properties,
5 pipeline entries, 5 milestones, 2 meetings).

Visit `http://localhost:8000/docs` for the OpenAPI explorer.

### Frontend

```bash
cd frontend
npm install
npm run dev                                  # http://localhost:5173
```

`frontend/.env` defaults `VITE_API_URL` to `http://localhost:8000`.

---

## French regulatory context encoded in the data

Per-commune flags carried in `backend/data/seeds/regulations.json`:

- `registration_required` — meublé touristique enregistrement
- `changement_usage` — strict / moderate / light / none
- `cap_120_days` — résidence principale annual cap
- `encadrement_loyers` — Lyon zones only
- `dpe_min_class` / `dpe_class_g_banned` — 2025 G ban, 2028 F ban planned

National 2026 constants (micro-BIC abattement, LMNP threshold, CFE
band, taxe de séjour range, PNO market rate) live in the same file
under `national_2026`.

---

## Anti-hallucination principles (enforced in code)

1. **Every number on screen traces to a service call, a seed
   constant, or a user input.** Synthetic values are tagged
   `synthetic: true` in the seed JSON.
2. **The margin calculator never invents costs.** Every line in the
   waterfall is sourced; the `source` field on each `WaterfallLine`
   names the underlying convention or regulation.
3. **LLM is constrained to language polish.** Briefing slots are
   filled in Python before Claude ever sees the prose. System prompt
   forbids numeric edits, entity edits, paragraph drops. Deterministic
   draft is the always-on backstop.
4. **Cost ledger gates LLM spend.** €50/mo ceiling; fails closed when
   budget is exhausted (Phase 4).
5. **Sources contradict → show both.** When AirDNA and AirROI disagree
   on a comp, the dashboard renders both with provenance tags rather
   than silently picking one.

---

## License

Internal EchoFrame Intelligence build. Projections are probabilistic
estimates from quantitative models and do not constitute financial or
investment advice. Confidence intervals reflect inherent uncertainty.
Past performance does not guarantee future results.

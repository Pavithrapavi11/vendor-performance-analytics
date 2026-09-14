# Vendor Performance Analytics — NorthBridge Supplies

A fresher-level, end-to-end analytics project for a fictional Indian industrial
distributor. **Vendor data → Python cleaning → SQL analysis → Power BI
dashboard → business recommendations.**

> **Business question:** Which three vendors should be placed on a Performance
> Improvement Plan this quarter, and which vendors should be considered for
> continued or increased business?
>
> The analysis *supports* the decision; it does not automatically recommend
> vendor replacement.

---

## Bottom-line result

| List   | Vendors (from the shipped run)                                   |
|--------|-------------------------------------------------------------------|
| **PIP**    | Ganga Industries (V002), Himalaya MRO (V010), Sundar Logistics (V005) |
| **Reward** | Krishna Traders (V003), Narmada Traders (V019), Deccan Distributors (V013) |

See `report/vendor_performance_report.pdf` for the full write-up and
`report/interview_deck.pdf` for the 5-slide summary.

---

## Repo layout

```
vendor-performance-analytics/
├── data/
│   ├── raw/            # generated CSVs (dirty, realistic)
│   ├── clean/          # cleaned CSVs after Python pipeline
│   └── sql_outputs/    # CSV output of every analysis query
├── sql/                # schema.sql + 9 numbered analysis files
├── notebooks/          # 01_cleaning.ipynb, 02_eda.ipynb
├── dashboard/
│   ├── dax_measures.dax        # copy/paste-ready Power BI measures
│   └── mockups/                # PNG mockups of the 2 dashboard pages
├── report/             # PDF report, PDF deck, ER diagram, all figures
├── scripts/            # data_generator, db_loader, cleaning, run_sql,
│                       # make_charts, make_report, run_all
├── INTERVIEW_NOTES.md
└── README.md
```

---

## Tech stack

- Python 3.11 — pandas, numpy, matplotlib, psycopg2, Faker, SQLAlchemy, ReportLab
- PostgreSQL 15/16 (SQL is 16-compatible)
- Power BI Desktop (dashboard delivered as DAX file + PNG mockups)
- **No** ML, seaborn, or web framework — intentionally kept simple.

---

## Reproducing the project end-to-end

1. **Postgres** — a database `northbridge` and role `nbuser` (password `nbpass`)
   with local access. Override with `PG_URL` env var if you use different
   creds.
2. **Python deps** —
   ```
   pip install pandas numpy matplotlib psycopg2-binary faker sqlalchemy reportlab jupyter
   ```
3. **Run the full pipeline**:
   ```
   python scripts/run_all.py
   ```
   which will:
   - regenerate the raw CSVs (deterministic seed = 42)
   - apply the schema and load raw data
   - run the cleaning pipeline (produces `*_clean` tables and cleaned CSVs)
   - execute every SQL file and save each `SELECT`'s output to
     `data/sql_outputs/`
   - regenerate every chart, both dashboard mockups, the PDF report, and
     the interview deck

Every step is idempotent — re-running produces the same numbers.

---

## Power BI

The `.pbix` file is intentionally not shipped (this environment doesn't have
Power BI Desktop). Instead, `dashboard/dax_measures.dax` contains every measure
already mapped to the SQL, and `dashboard/mockups/` shows exactly what the two
dashboard pages should look like:

1. **Page 1 — Executive Summary**: KPI cards, vendor leaderboard, monthly OTD /
   defect trend, category heatmap, region/category/month slicers.
2. **Page 2 — Vendor Deep-Dive**: drill-through by vendor with delivery
   buckets, price-variance-vs-order-size scatter, monthly quality trend,
   inspection-coverage comparison.

To rebuild the `.pbix`:
- open Power BI Desktop
- Get Data → PostgreSQL (or Text/CSV against the four `*_clean.csv` files)
- import the tables, then paste each measure from `dax_measures.dax`
- lay out the pages using the mockup PNGs as reference

---

## KPI definitions (single source of truth)

| KPI                   | Formula                                                        | Scope                                              |
|-----------------------|----------------------------------------------------------------|----------------------------------------------------|
| On-Time Delivery %    | `count(actual ≤ promised) / count(delivered)`                  | Missing actual date excluded from denominator      |
| Defect Rate %         | `Σ defect_count / Σ inspected_qty × 100`                       | Inspected POs only                                 |
| Price Variance %      | `(unit_price − agreed_price) / agreed_price × 100`             | Rows with `agreed_price = 0 / NULL` excluded       |
| Lead Time (days)      | `actual_delivery_date − order_date`                            | Missing actual date excluded                       |
| Fill Rate %           | `min(100, quantity_received / quantity_ordered × 100)`         | Over-shipments capped, flagged in a DQ view        |
| Composite Score       | `0.4·OTD + 0.4·(100−Defect) + 0.2·(100−max(0,PriceVariance))`  | Eligibility ≥ 20 POs. Weights academic, not industry-standard |

## PIP shortlist logic (defensible)

1. Eligible vendors have ≥ 20 POs.
2. Rank eligible vendors by composite score ascending.
3. Shortlist the bottom 3 **only** if each has below-average OTD % OR
   above-average defect rate %. Otherwise skip and take the next lowest.
4. For each PIP vendor, the report explains selection using OTD %, Defect %,
   Fill %, and Composite score.

## Reward shortlist logic

Top 3 eligible vendors by composite score, explained with the same KPIs.

---

## Explicit limitations

- No sole-source vendor logic — a low-scoring vendor may be irreplaceable
- No total-cost-of-ownership calc — price variance labelled as *estimated*
- Quality metrics reflect only inspected POs; vendors with low inspection
  coverage have less reliable scores
- Synthetic dataset — patterns are illustrative, not real market behaviour
- Composite-score weights are chosen for this academic project, not
  industry-standard
- Small samples excluded via the ≥ 20 PO rule (Ashoka Papers, 17 POs, is
  ineligible even with a low score)

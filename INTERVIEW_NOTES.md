# Interview Notes — Vendor Performance Analytics

A cheat-sheet of the questions a first-round Data-/Business-Analyst interviewer
is most likely to ask on this project, with short answers you can defend.

---

## 1. Project & business context

**Q. Walk me through the project in 60 seconds.**
NorthBridge Supplies procures from 20 vendors. I built an end-to-end analytics
pipeline — synthetic data → Python cleaning → PostgreSQL SQL analysis → Power BI
dashboard → PDF report — that surfaces three PIP candidates and three reward
candidates each quarter. The report supports the decision; it doesn't replace
the category manager.

**Q. Why not just use a spreadsheet?**
Volume is fine for Excel, but a repeatable quarterly review needs (1) versioned
cleaning rules, (2) SQL queries anyone can re-run, (3) a dashboard business
users can filter without waiting for me. Excel can't give you all three.

**Q. Who is the audience?**
Head of Procurement (KPI cards, PIP/reward list) and category managers
(vendor deep-dive drill-through).

---

## 2. Data & modelling

**Q. Why a 4-table schema and not a single flat table?**
Vendors and products are dimensions; POs are the fact table. Separating them
avoids updating the vendor name in 1,400 places when it changes, and makes
category/region slicers trivial in Power BI. Quality inspections is 1:0..1
with POs — only ~60% of POs get inspected — so it's its own table with a
UNIQUE constraint on po_number.

**Q. Why UNIQUE on `quality_inspections.po_number`?**
Business rule: one inspection record per PO. The UNIQUE constraint enforces
that at the database level so a bug in the loader can't create ghost duplicate
inspections that inflate defect counts.

**Q. Why LEFT JOIN quality_inspections in your KPI queries?**
Only a subset of POs are inspected. A regular INNER JOIN would silently drop
vendors and POs from the OTD / spend calculations. LEFT JOIN keeps them, and I
compute defect rate only over rows where inspection actually happened.

---

## 3. Cleaning decisions

**Q. What did you actually clean?**
Six things, all logged in `01_cleaning.ipynb`:
1. Vendor name casing (3 rows, `.str.title()`)
2. Duplicate POs (10 rows, drop on `po_number` keep=first)
3. `agreed_price = 0` or NULL (5 rows) — flagged, kept, excluded from price
   variance
4. Missing `actual_delivery_date` (~1%) — legitimate in-transit, excluded from
   OTD denominator
5. Over-shipments (`received > ordered`, ~372 rows) — flagged in a data-quality
   view, fill-rate capped at 100%
6. Missing `defect_count` — filled 0 only when `quality_status = 'Passed'`;
   otherwise left NaN so it's excluded from defect calc

**Q. Why fill missing defect count with 0 only when status = 'Passed'?**
"Passed with no recorded defect" is a plausible ERP behaviour — someone
skipped the field. "Failed with no recorded defect" is a data-integrity issue
we shouldn't hide by filling 0.

---

## 4. KPIs & scoring

**Q. Explain your composite score.**
`0.40 × OTD % + 0.40 × (100 − Defect %) + 0.20 × (100 − max(0, PriceVariance %))`.
Delivery and quality get equal top weight (40 each) because both create
production downtime. Cost gets 20 because a 3% overprice hurts less than a
one-week stockout. Weights are documented as academic, not industry-standard.

**Q. Why cap negative price variance at 0 in the score?**
A vendor giving us a discount shouldn't push their score above 100. In the raw
price-variance table we show the negative number truthfully.

**Q. Why the ≥ 20 PO eligibility rule?**
Small samples produce noisy KPIs. Two POs both delivered late gives you a "0%
OTD" that isn't actionable. Ashoka Papers has 17 POs and a low score — under
the rule they aren't shortlisted; the report calls this out.

---

## 5. PIP selection

**Q. Why not just take the bottom 3 by score?**
Because a vendor can score low purely on price variance and still be perfectly
reliable on delivery and quality — putting them on PIP would be a bad
management action. The filter (below-avg OTD OR above-avg defect rate) makes
sure PIP flags a real operational issue.

**Q. What if none of the bottom-3 have an issue?**
The SQL walks down the ranking and picks the next vendor that does. In this
dataset all three bottom vendors have operational issues, so it wasn't needed
— but the logic is there.

---

## 6. SQL / Python specifics

**Q. Which SQL feature was most useful?**
CTEs — for readability — and window functions. `RANK() PARTITION BY category`
gave me the leaderboard within each category, and `LAG()` gave me month-over-
month OTD change per vendor, both without extra joins.

**Q. Why PostgreSQL and not SQLite / MySQL?**
Free, standards-compliant, `FILTER (WHERE …)` inside aggregates, and
`DATE_TRUNC` — cleaner SQL than the equivalent in SQLite or MySQL.

---

## 7. Limitations (the "what would you improve" question)

- No sole-source vendor logic — a low-scoring vendor may be irreplaceable
- No total-cost-of-ownership — price variance is estimated, ignores freight
  and rejects
- Quality metrics only on the ~60% of POs that were inspected
- Weights are illustrative — a real project would run sensitivity analysis
- Synthetic data — the patterns are demonstrations, not real behaviour
- No forecasting — this is descriptive analytics, deliberately

**One-sentence answer to "what would you build next?":**
Sensitivity analysis on the composite weights, plus a spend-weighted variant of
the score so heavy vendors count more than tail vendors.

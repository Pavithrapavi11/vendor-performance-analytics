"""
Generate the two Jupyter notebooks (01_cleaning.ipynb, 02_eda.ipynb) as
proper .ipynb files, then execute them so the outputs are embedded.
"""
import subprocess
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
NB   = ROOT / "notebooks"
NB.mkdir(exist_ok=True)


def make(nb_path: Path, cells: list):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    }
    nb_path.write_text(nbf.writes(nb))
    print(f"wrote {nb_path.name}")


# =========================================================================
# 01_cleaning.ipynb
# =========================================================================
md1_intro = """\
# 01 — Data Cleaning

**Goal:** produce four clean tables — `vendors_clean`, `products_clean`,
`purchase_orders_clean`, `quality_inspections_clean` — from the raw CSVs, and
log every cleaning decision in plain English so the interviewer can defend
every number.

**Cleaning decisions made in this notebook:**
1. Vendor-name casing — two vendor names had inconsistent casing; normalised
   with `.str.title()`.
2. Duplicate POs — the raw file contains a handful of exact duplicates
   (accidental double-entry). Drop on `po_number`, keep first.
3. Missing `actual_delivery_date` (~1%) — a legitimate "in transit" state.
   Kept as `NaT`; excluded from the OTD denominator downstream.
4. `agreed_price = 0` or `NULL` (< 1%) — flagged and excluded from price
   variance.
5. `quantity_received > quantity_ordered` — realistic over-shipments. Left
   truthfully in the data; fill rate is capped at 100 % in the SQL layer and
   these rows are flagged in a DQ view.
6. Missing `defect_count` (~2 %) — filled with 0 only when
   `quality_status = 'Passed'`. Otherwise left `NaN` (so the row is excluded
   from defect calculations rather than silently zeroed).
7. Inspection coverage — only ~60 % of POs get inspected. This is a business
   fact, not a data-quality problem. Documented explicitly so the interviewer
   sees the LEFT-JOIN choice below is intentional.
"""

md1_profile = """\
## Profiling — shape, dtypes, nulls, coverage
"""

code1_profile = """\
import pandas as pd
from pathlib import Path

RAW = Path.cwd().parent / "data" / "raw"

v  = pd.read_csv(RAW / "vendors.csv",             parse_dates=["contract_start_date"])
p  = pd.read_csv(RAW / "products.csv")
po = pd.read_csv(RAW / "purchase_orders.csv",
                 parse_dates=["order_date", "promised_date", "actual_delivery_date"])
qi = pd.read_csv(RAW / "quality_inspections.csv", parse_dates=["inspection_date"])

for name, df in {"vendors": v, "products": p,
                 "purchase_orders": po, "quality_inspections": qi}.items():
    print(f"--- {name} ---")
    print(f"  shape:      {df.shape}")
    print(f"  duplicates: {df.duplicated().sum()}")
    print(f"  nulls:      {df.isna().sum().to_dict()}")
    print()

# Coverage
insp_pos = qi['po_number'].nunique()
uniq_pos = po['po_number'].nunique()
print(f"Inspection coverage: {insp_pos}/{uniq_pos} = {100*insp_pos/uniq_pos:.1f}%")
"""

md1_apply = """\
## Apply the cleaning pipeline

The full pipeline lives in `scripts/cleaning.py`. We call it here so the
notebook prints the decision log inline.
"""

code1_apply = """\
import sys
sys.path.insert(0, str(Path.cwd().parent / "scripts"))
from cleaning import load_raw, clean, save_to_csv, save_to_db

raw     = load_raw()
cleaned, log = clean(raw)
save_to_csv(cleaned)
save_to_db(cleaned)   # writes *_clean tables to Postgres

print("Cleaning decision log:")
for k, val in log.items():
    print(f"  {k:35s}  {val}")
"""

md1_after = """\
## Post-clean sanity checks
"""

code1_after = """\
po_c = cleaned['purchase_orders']
qi_c = cleaned['quality_inspections']
v_c  = cleaned['vendors']

print("Vendors after casing fix:")
print(v_c['vendor_name'].tolist())

print(f"\\nPOs after de-dup: {len(po_c)}")
print(f"Missing actual_delivery_date: {po_c['actual_delivery_date'].isna().sum()}")
print(f"Over-shipments still flagged: {(po_c['quantity_received'] > po_c['quantity_ordered']).sum()}")
print(f"Inspected POs: {len(qi_c)}")
print(f"Missing defect_count (should be Failed/Conditional only): {qi_c['defect_count'].isna().sum()}")
"""

make(NB / "01_cleaning.ipynb", [
    nbf.v4.new_markdown_cell(md1_intro),
    nbf.v4.new_markdown_cell(md1_profile),
    nbf.v4.new_code_cell(code1_profile),
    nbf.v4.new_markdown_cell(md1_apply),
    nbf.v4.new_code_cell(code1_apply),
    nbf.v4.new_markdown_cell(md1_after),
    nbf.v4.new_code_cell(code1_after),
])

# =========================================================================
# 02_eda.ipynb
# =========================================================================
md2_intro = """\
# 02 — Exploratory Data Analysis

Working on the cleaned tables (`*_clean`), we look for the patterns that will
drive the SQL analysis and the dashboard:

- Order volume distribution across vendors
- Monthly on-time delivery trend
- Defect-rate distribution (inspected POs only)
- Delivery-delay histogram
- Price variance by category
- Inspection coverage per vendor

All charts use Matplotlib only (no seaborn) per project constraints.
"""

code2_setup = """\
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

CLEAN = Path.cwd().parent / "data" / "clean"
FIG   = Path.cwd().parent / "report" / "figures"

po = pd.read_csv(CLEAN / "purchase_orders_clean.csv",
                 parse_dates=["order_date", "promised_date", "actual_delivery_date"])
v  = pd.read_csv(CLEAN / "vendors_clean.csv")
qi = pd.read_csv(CLEAN / "quality_inspections_clean.csv")
po.shape, v.shape, qi.shape
"""

md2_vol = """\
## Order volume by vendor

Uneven volume — a handful of heavy suppliers and a long tail of light ones.
This is why the composite score has a ≥ 20 PO eligibility rule: small-sample
vendors give noisy KPIs.
"""

code2_vol = """\
vol = po.groupby("vendor_id").size().reset_index(name="pos").merge(
        v[["vendor_id", "vendor_name"]], on="vendor_id"
      ).sort_values("pos")

fig, ax = plt.subplots(figsize=(8,5))
ax.barh(vol["vendor_name"], vol["pos"], color="#0E7C86")
ax.set_title("PO volume by vendor"); ax.set_xlabel("PO count")
plt.tight_layout(); plt.show()
"""

md2_otd = """\
## Monthly on-time delivery — average and one declining vendor

The average line is roughly flat; but V005 (Sundar Logistics) drops after
month 4 — a directional issue that an annual average would hide.
"""

code2_otd = """\
po['is_late']     = po['actual_delivery_date'] > po['promised_date']
po['delivered']   = po['actual_delivery_date'].notna()
po['month']       = po['order_date'].dt.to_period('M').dt.to_timestamp()

def otd(group):
    d = group['delivered'].sum()
    if d == 0: return None
    return 100 * (group['delivered'].sum() - group['is_late'].sum()) / d

monthly_all = po.groupby('month').apply(otd).reset_index(name='otd_pct')
v005 = po[po['vendor_id'] == 'V005'].groupby('month').apply(otd).reset_index(name='otd_pct')

fig, ax = plt.subplots(figsize=(9,4))
ax.plot(monthly_all['month'], monthly_all['otd_pct'], marker='o', color='#1D3557', label='All vendors')
ax.plot(v005['month'], v005['otd_pct'], marker='s', color='#E76F51', label='V005 Sundar Logistics')
ax.set_title('Monthly on-time delivery %'); ax.set_ylabel('OTD %')
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.legend(); plt.tight_layout(); plt.show()
"""

md2_def = """\
## Defect distribution (inspected POs only)

Long right tail. Most inspections show < 5 % defect rate; a handful spike
above 10 %. Note this is over inspected POs — non-inspected POs are excluded.
"""

code2_def = """\
qi_ok = qi.dropna(subset=['defect_count'])
dr = 100 * qi_ok['defect_count'] / qi_ok['inspected_quantity']

fig, ax = plt.subplots(figsize=(8,4))
ax.hist(dr, bins=30, color='#0E7C86', edgecolor='white')
ax.set_title('Defect rate distribution (inspected POs)')
ax.set_xlabel('Defect rate %'); ax.set_ylabel('Number of inspections')
plt.tight_layout(); plt.show()
"""

md2_delay = """\
## Delivery-delay histogram

Delay in days after the promised date. Centre is near zero with a long right
tail — when a vendor misses, they tend to miss badly.
"""

code2_delay = """\
delivered = po.dropna(subset=['actual_delivery_date']).copy()
delivered['delay'] = (delivered['actual_delivery_date'] - delivered['promised_date']).dt.days

fig, ax = plt.subplots(figsize=(8,4))
ax.hist(delivered['delay'], bins=30, color='#E76F51', edgecolor='white')
ax.axvline(0, color='#1D3557', linestyle='--')
ax.set_title('Delivery delay (days after promised)')
ax.set_xlabel('Delay days'); ax.set_ylabel('POs')
plt.tight_layout(); plt.show()
"""

md2_price = """\
## Price variance by category
"""

code2_price = """\
m = po.merge(v[['vendor_id', 'vendor_category']], on='vendor_id')
m = m[m['agreed_price'] > 0].copy()
m['var_pct'] = 100 * (m['unit_price'] - m['agreed_price']) / m['agreed_price']
cats = m['vendor_category'].unique()
data = [m.loc[m['vendor_category'] == c, 'var_pct'].values for c in cats]

fig, ax = plt.subplots(figsize=(8,4))
bp = ax.boxplot(data, tick_labels=cats, patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('#E9C46A')
ax.set_title('Price variance % by category'); ax.set_ylabel('Variance %')
plt.tight_layout(); plt.show()
"""

md2_cover = """\
## Inspection coverage per vendor

Vendors with low inspection coverage have less reliable quality scores.
This is a documented limitation of the composite score.
"""

code2_cover = """\
cov = po.groupby('vendor_id').size().reset_index(name='total_pos')
insp = qi.merge(po[['po_number','vendor_id']], on='po_number').groupby('vendor_id').size().reset_index(name='inspected')
cov = cov.merge(insp, on='vendor_id', how='left').fillna(0)
cov['pct'] = 100 * cov['inspected'] / cov['total_pos']
cov = cov.merge(v[['vendor_id','vendor_name']], on='vendor_id').sort_values('pct')

fig, ax = plt.subplots(figsize=(8,5))
ax.barh(cov['vendor_name'], cov['pct'], color='#1D3557')
ax.set_title('Inspection coverage % by vendor'); ax.set_xlabel('% of POs inspected')
plt.tight_layout(); plt.show()
"""

md2_close = """\
## Takeaways for the SQL layer

- Use LEFT JOIN on `quality_inspections_clean` so non-inspected POs stay in
  vendor totals but only inspected rows drive the defect-rate calculation.
- Exclude missing-actual-date rows from the OTD denominator.
- Compare pre-M4 and post-M4 windows to catch quality regressions the
  average would hide (V005).
- Require ≥ 20 POs for eligibility on the composite score.
"""

make(NB / "02_eda.ipynb", [
    nbf.v4.new_markdown_cell(md2_intro),
    nbf.v4.new_code_cell(code2_setup),
    nbf.v4.new_markdown_cell(md2_vol),
    nbf.v4.new_code_cell(code2_vol),
    nbf.v4.new_markdown_cell(md2_otd),
    nbf.v4.new_code_cell(code2_otd),
    nbf.v4.new_markdown_cell(md2_def),
    nbf.v4.new_code_cell(code2_def),
    nbf.v4.new_markdown_cell(md2_delay),
    nbf.v4.new_code_cell(code2_delay),
    nbf.v4.new_markdown_cell(md2_price),
    nbf.v4.new_code_cell(code2_price),
    nbf.v4.new_markdown_cell(md2_cover),
    nbf.v4.new_code_cell(code2_cover),
    nbf.v4.new_markdown_cell(md2_close),
])

print("\nExecuting notebooks so outputs are embedded...")
for nb_file in ["01_cleaning.ipynb", "02_eda.ipynb"]:
    print(f"  running {nb_file}")
    r = subprocess.run(
        [sys.executable, "-m", "jupyter", "nbconvert",
         "--to", "notebook", "--execute", "--inplace",
         "--ExecutePreprocessor.timeout=120",
         str(NB / nb_file)],
        capture_output=True, text=True,
    )
    if r.returncode:
        print(r.stderr[-800:])
    else:
        print("    ok")

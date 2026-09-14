"""
Cleaning pipeline — produces cleaned DataFrames and writes them back to
PostgreSQL as *_clean tables. Called by the 01_cleaning notebook and by the
run_all.py orchestrator.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PG_URL   = os.environ.get(
    "PG_URL",
    "postgresql+psycopg2://nbuser:nbpass@localhost:5432/northbridge",
)


def load_raw() -> dict[str, pd.DataFrame]:
    raw = DATA_DIR / "raw"
    return {
        "vendors":  pd.read_csv(raw / "vendors.csv",  parse_dates=["contract_start_date"]),
        "products": pd.read_csv(raw / "products.csv"),
        "purchase_orders": pd.read_csv(
            raw / "purchase_orders.csv",
            parse_dates=["order_date", "promised_date", "actual_delivery_date"],
        ),
        "quality_inspections": pd.read_csv(
            raw / "quality_inspections.csv", parse_dates=["inspection_date"]
        ),
    }


def clean(dfs: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], dict]:
    """Return cleaned frames + a decisions dict for reporting."""
    v, p, po, qi = (dfs["vendors"].copy(), dfs["products"].copy(),
                    dfs["purchase_orders"].copy(), dfs["quality_inspections"].copy())
    log: dict = {}

    # 1. Vendor name casing --------------------------------------------------
    log["vendor_name_casing_fixed"] = int(
        (v["vendor_name"] != v["vendor_name"].str.title()).sum()
    )
    v["vendor_name"] = v["vendor_name"].str.title().str.strip()

    # 2. Duplicate POs -------------------------------------------------------
    dup_mask = po.duplicated(subset="po_number", keep="first")
    log["duplicate_pos_dropped"] = int(dup_mask.sum())
    po = po.loc[~dup_mask].copy()

    # 3. Zero / null agreed_price flagged (kept, but excluded from variance) --
    log["agreed_price_zero_or_null"] = int(
        ((po["agreed_price"].isna()) | (po["agreed_price"] == 0)).sum()
    )

    # 4. Missing actual_delivery_date is legitimate — leave NaT, exclude from OTD
    log["missing_actual_delivery"] = int(po["actual_delivery_date"].isna().sum())

    # 5. Over-shipments flagged (kept truthfully; fill rate capped in SQL) ----
    log["overshipments_flagged"] = int((po["quantity_received"] > po["quantity_ordered"]).sum())

    # 6. Missing defect_count: fill 0 ONLY when quality_status == 'Passed',
    #    otherwise flag & drop from defect calc.
    missing_defect = qi["defect_count"].isna()
    fill_zero      = missing_defect & (qi["quality_status"] == "Passed")
    qi.loc[fill_zero, "defect_count"] = 0
    log["defect_count_filled_zero"] = int(fill_zero.sum())
    log["defect_count_still_missing"] = int(qi["defect_count"].isna().sum())

    # 7. Data types ----------------------------------------------------------
    qi["defect_count"] = qi["defect_count"].astype("Int64")

    # 8. Cast timestamp columns back to python date so PostgreSQL infers DATE.
    #    (pandas.to_sql maps datetime64 -> TIMESTAMP, which breaks
    #    date arithmetic in later SQL queries.)
    for col in ("contract_start_date",):
        v[col] = pd.to_datetime(v[col]).dt.date
    for col in ("order_date", "promised_date", "actual_delivery_date"):
        po[col] = pd.to_datetime(po[col]).dt.date
    for col in ("inspection_date",):
        qi[col] = pd.to_datetime(qi[col]).dt.date

    return {"vendors": v, "products": p,
            "purchase_orders": po, "quality_inspections": qi}, log


def save_to_db(clean_dfs: dict[str, pd.DataFrame]):
    engine = create_engine(PG_URL)
    with engine.begin() as conn:
        for name, df in clean_dfs.items():
            table = f"{name}_clean"
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        clean_dfs["vendors"].to_sql("vendors_clean", conn, index=False)
        clean_dfs["products"].to_sql("products_clean", conn, index=False)
        clean_dfs["purchase_orders"].to_sql("purchase_orders_clean", conn, index=False)
        clean_dfs["quality_inspections"].to_sql("quality_inspections_clean",
                                                conn, index=False)


def save_to_csv(clean_dfs: dict[str, pd.DataFrame]):
    out = DATA_DIR / "clean"
    out.mkdir(exist_ok=True)
    for name, df in clean_dfs.items():
        df.to_csv(out / f"{name}_clean.csv", index=False)


if __name__ == "__main__":
    raw = load_raw()
    cleaned, log = clean(raw)
    save_to_csv(cleaned)
    save_to_db(cleaned)
    print("Cleaning decisions:")
    for k, v in log.items():
        print(f"  {k}: {v}")
    print("Saved cleaned CSVs and *_clean tables.")

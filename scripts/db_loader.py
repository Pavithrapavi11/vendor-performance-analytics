"""
Load raw CSVs into PostgreSQL — NorthBridge Supplies.

Usage:
    python db_loader.py            # loads raw CSVs into base tables
    python db_loader.py --clean    # loads cleaned CSVs into *_clean tables
"""

import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT     = Path(__file__).resolve().parent.parent
SQL_DIR  = ROOT / "sql"
DATA_DIR = ROOT / "data"

PG_URL = os.environ.get(
    "PG_URL",
    "postgresql+psycopg2://nbuser:nbpass@localhost:5432/northbridge",
)


def apply_schema(engine):
    schema_sql = (SQL_DIR / "schema.sql").read_text()
    with engine.begin() as conn:
        for stmt in schema_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    print("[ok] schema applied")


def load_raw(engine):
    raw = DATA_DIR / "raw"
    v  = pd.read_csv(raw / "vendors.csv",             parse_dates=["contract_start_date"])
    p  = pd.read_csv(raw / "products.csv")
    po = pd.read_csv(raw / "purchase_orders.csv",
                     parse_dates=["order_date", "promised_date", "actual_delivery_date"])
    qi = pd.read_csv(raw / "quality_inspections.csv", parse_dates=["inspection_date"])

    # Drop duplicate PO rows so PK insert works. Cleaning notebook demonstrates
    # this decision; here we just enforce it so raw load succeeds.
    po = po.drop_duplicates(subset="po_number", keep="first")

    v.to_sql("vendors",             engine, if_exists="append", index=False)
    p.to_sql("products",            engine, if_exists="append", index=False)
    po.to_sql("purchase_orders",    engine, if_exists="append", index=False)
    qi.to_sql("quality_inspections", engine, if_exists="append", index=False)
    print(f"[ok] loaded raw: vendors={len(v)}, products={len(p)}, "
          f"POs={len(po)}, inspections={len(qi)}")


def load_clean(engine):
    """Load cleaned dataframes into *_clean tables (called from the notebook)."""
    raise NotImplementedError(
        "Use the cleaning notebook's save_clean_to_db() helper instead."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop & recreate schema")
    args = parser.parse_args()

    engine = create_engine(PG_URL)
    if args.reset:
        apply_schema(engine)
    load_raw(engine)


if __name__ == "__main__":
    main()

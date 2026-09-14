"""
Run all SQL analysis files and save each SELECT output to /data/sql_outputs.

Usage:  python scripts/run_sql.py
"""
import os
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT   = Path(__file__).resolve().parent.parent
SQLDIR = ROOT / "sql"
OUT    = ROOT / "data" / "sql_outputs"
OUT.mkdir(parents=True, exist_ok=True)

PG_URL = os.environ.get(
    "PG_URL",
    "postgresql+psycopg2://nbuser:nbpass@localhost:5432/northbridge",
)
engine = create_engine(PG_URL)


def split_statements(sql: str) -> list[str]:
    # crude splitter that respects semicolons outside comments
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        lines.append(line)
    joined = "\n".join(lines)
    return [s.strip() for s in joined.split(";") if s.strip()]


for f in sorted(SQLDIR.glob("[0-9]*_*.sql")):
    stem = f.stem
    print(f"\n== {stem} ==")
    stmts = split_statements(f.read_text())
    with engine.begin() as conn:
        select_idx = 0
        for stmt in stmts:
            head = stmt.split()[0].upper()
            if head in ("CREATE", "DROP"):
                conn.execute(text(stmt))
                print(f"  [ddl] {head}")
                continue
            # WITH / SELECT are both queries returning rows
            if head not in ("SELECT", "WITH"):
                conn.execute(text(stmt))
                continue
            df = pd.read_sql(text(stmt), conn)
            select_idx += 1
            out = OUT / f"{stem}__q{select_idx}.csv"
            df.to_csv(out, index=False)
            print(f"  [ok] q{select_idx}: {len(df)} rows -> {out.name}")

"""
End-to-end orchestrator: regenerates every artefact in this repo.

Steps:
  1. data_generator.py       (raw CSVs)
  2. db_loader.py --reset    (schema + raw tables in Postgres)
  3. cleaning.py             (clean CSVs + *_clean tables)
  4. run_sql.py              (every SQL query, outputs to /data/sql_outputs)
  5. make_charts.py          (all matplotlib figures + dashboard mockups)
  6. make_report.py          (PDF report + PDF deck)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYS = [
    ["scripts/data_generator.py"],
    ["scripts/db_loader.py", "--reset"],
    ["scripts/cleaning.py"],
    ["scripts/run_sql.py"],
    ["scripts/make_charts.py"],
    ["scripts/make_report.py"],
]
for step in PYS:
    print(f"\n>>> {' '.join(step)}")
    r = subprocess.run([sys.executable] + step, cwd=ROOT)
    if r.returncode:
        sys.exit(f"step failed: {step}")
print("\nAll artefacts regenerated.")

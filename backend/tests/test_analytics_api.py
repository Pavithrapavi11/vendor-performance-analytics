"""Backend API tests for Vendor Performance Analytics."""
import os
import io
import csv
import pytest
import requests
from pathlib import Path

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read from frontend .env
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"
DEMO_DIR = Path("/app/vendor-performance-analytics/data/raw")


@pytest.fixture(scope="module")
def demo_files():
    return {
        "vendors": (DEMO_DIR / "vendors.csv").read_bytes(),
        "purchase_orders": (DEMO_DIR / "purchase_orders.csv").read_bytes(),
        "quality_inspections": (DEMO_DIR / "quality_inspections.csv").read_bytes(),
        "products": (DEMO_DIR / "products.csv").read_bytes(),
    }


# ---- Schema ----------------------------------------------------------------
def test_schema():
    r = requests.get(f"{API}/analytics/schema", timeout=30)
    assert r.status_code == 200
    data = r.json()
    for k in ("required_files", "optional_files", "columns", "notes"):
        assert k in data
    for k in ("vendors", "products", "purchase_orders", "quality_inspections"):
        assert k in data["columns"]


# ---- Datasets listing ------------------------------------------------------
def test_datasets_list_has_demo():
    r = requests.get(f"{API}/analytics/datasets", timeout=30)
    assert r.status_code == 200
    ds = r.json()["datasets"]
    demo = [d for d in ds if d["id"] == "demo"]
    assert len(demo) == 1
    assert demo[0]["source"] == "seed"


# ---- Demo summary correctness ---------------------------------------------
def test_demo_summary_correctness():
    r = requests.get(f"{API}/analytics/demo/summary", timeout=60)
    assert r.status_code == 200
    s = r.json()
    for k in ("totals", "averages", "benchmarks", "cleaning_log",
              "leaderboard", "pip", "reward", "category", "monthly",
              "delivery_buckets", "decline"):
        assert k in s, f"missing key {k}"
    assert s["totals"]["total_pos"] == 1400

    assert 58 <= s["averages"]["otd_pct"] <= 60, s["averages"]
    assert 2 <= s["averages"]["defect_rate_pct"] <= 3, s["averages"]
    assert 80 <= s["averages"]["composite_score"] <= 84, s["averages"]

    # PIP order + names
    pip_ids = [x["vendor_id"] for x in s["pip"]]
    assert pip_ids == ["V002", "V010", "V005"], pip_ids
    pip_names = [x["vendor_name"] for x in s["pip"]]
    assert pip_names == ["Ganga Industries", "Himalaya Mro", "Sundar Logistics"]
    for e in s["pip"]:
        assert "benchmark_otd" in e and "benchmark_defect" in e

    # Reward
    reward_ids = [x["vendor_id"] for x in s["reward"]]
    assert reward_ids == ["V003", "V019", "V013"], reward_ids
    reward_names = [x["vendor_name"] for x in s["reward"]]
    assert reward_names == ["Krishna Traders", "Narmada Traders", "Deccan Distributors"]

    # Leaderboard
    assert len(s["leaderboard"]) == 20
    scores = [x["composite_score"] for x in s["leaderboard"]]
    assert scores[0] >= scores[-1]


# ---- Upload happy path -----------------------------------------------------
_uploaded_id = {}


def test_upload_demo_csvs(demo_files):
    files = {
        "vendors": ("vendors.csv", demo_files["vendors"], "text/csv"),
        "purchase_orders": ("purchase_orders.csv", demo_files["purchase_orders"], "text/csv"),
        "quality_inspections": ("quality_inspections.csv", demo_files["quality_inspections"], "text/csv"),
        "products": ("products.csv", demo_files["products"], "text/csv"),
    }
    r = requests.post(f"{API}/analytics/upload",
                      files=files, data={"name": "TEST_upload_ds"}, timeout=120)
    assert r.status_code == 200, r.text
    entry = r.json()
    assert entry["name"] == "TEST_upload_ds"
    assert entry["source"] == "upload"
    assert entry["totals"]["total_pos"] == 1400
    _uploaded_id["id"] = entry["id"]

    # Now GET summary and validate identical PIP/reward
    sr = requests.get(f"{API}/analytics/{entry['id']}/summary", timeout=60)
    assert sr.status_code == 200
    s = sr.json()
    assert [x["vendor_id"] for x in s["pip"]] == ["V002", "V010", "V005"]
    assert [x["vendor_id"] for x in s["reward"]] == ["V003", "V019", "V013"]


def test_upload_malformed_csv(demo_files):
    # Strip vendor_id column from vendors.csv
    import pandas as pd
    df = pd.read_csv(io.BytesIO(demo_files["vendors"]))
    df = df.drop(columns=["vendor_id"])
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    files = {
        "vendors": ("vendors.csv", buf.getvalue(), "text/csv"),
        "purchase_orders": ("purchase_orders.csv", demo_files["purchase_orders"], "text/csv"),
        "quality_inspections": ("quality_inspections.csv", demo_files["quality_inspections"], "text/csv"),
    }
    r = requests.post(f"{API}/analytics/upload",
                      files=files, data={"name": "TEST_bad"}, timeout=60)
    assert r.status_code == 400
    assert "vendor_id" in r.text


def test_cannot_delete_demo():
    r = requests.delete(f"{API}/analytics/demo", timeout=30)
    assert r.status_code == 400


def test_delete_uploaded():
    ds_id = _uploaded_id.get("id")
    if not ds_id:
        pytest.skip("no uploaded dataset available")
    r = requests.delete(f"{API}/analytics/{ds_id}", timeout=30)
    assert r.status_code == 200
    # Confirm not in list
    lst = requests.get(f"{API}/analytics/datasets", timeout=30).json()["datasets"]
    assert not any(d["id"] == ds_id for d in lst)


# ---- Legacy static assets --------------------------------------------------
@pytest.mark.parametrize("path", ["/analytics/report.pdf", "/analytics/deck.pdf"])
def test_legacy_static_assets(path):
    r = requests.get(f"{BASE_URL}{path}", timeout=30)
    assert r.status_code == 200, f"{path} -> {r.status_code}"

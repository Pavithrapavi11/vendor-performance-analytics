from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import io
import os
import logging
import shutil
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel, Field, ConfigDict

from analytics import SCHEMA, DataError, build_summary


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Demo dataset lives inside the local analytics repo
DEMO_DIR = ROOT_DIR.parent / "data" / "raw"
UPLOAD_ROOT = ROOT_DIR / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# In-memory cache of computed summaries (dataset_id -> summary dict)
_summary_cache: dict[str, dict] = {}
# In-memory dataset registry (id -> {name, source, files, created_at})
_datasets: dict[str, dict] = {}

app = FastAPI(title="NorthBridge Vendor Analytics")
api_router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
def _load_frames(folder: Path) -> dict[str, pd.DataFrame]:
    """Load the four CSVs from a directory. products.csv is optional."""
    frames = {}
    for name in ("vendors", "purchase_orders", "quality_inspections"):
        f = folder / f"{name}.csv"
        if not f.exists():
            raise DataError(f"missing required file: {name}.csv")
        frames[name] = pd.read_csv(f)
    prod = folder / "products.csv"
    frames["products"] = pd.read_csv(prod) if prod.exists() else None
    return frames


def _compute(dataset_id: str, folder: Path) -> dict:
    """Compute and cache the analytics summary for a dataset directory."""
    if dataset_id in _summary_cache:
        return _summary_cache[dataset_id]
    frames = _load_frames(folder)
    summary = build_summary(
        vendors=frames["vendors"],
        po=frames["purchase_orders"],
        qi=frames["quality_inspections"],
        products=frames["products"],
    )
    _summary_cache[dataset_id] = summary
    return summary


def _dataset_folder(dataset_id: str) -> Path:
    if dataset_id == "demo":
        return DEMO_DIR
    folder = UPLOAD_ROOT / dataset_id
    if not folder.exists():
        raise HTTPException(404, f"dataset '{dataset_id}' not found")
    return folder


# --- Discovery ------------------------------------------------------------
@api_router.get("/analytics/schema")
async def analytics_schema():
    return {
        "required_files": ["vendors.csv", "purchase_orders.csv",
                        "quality_inspections.csv"],
        "optional_files": ["products.csv"],
        "columns": SCHEMA,
        "notes": [
            "CSV headers must match the column names exactly.",
            "Dates must parse as ISO (YYYY-MM-DD) or standard formats.",
            "quality_inspections is expected to cover a SUBSET of POs "
            "(1:0..1 with purchase_orders on po_number).",
        ],
    }


@api_router.get("/analytics/datasets")
async def list_datasets():
    demo_entry = {
        "id":         "demo",
        "name":       "NorthBridge Supplies (demo)",
        "source":     "seed",
        "created_at": None,
        "files":      ["vendors.csv", "products.csv",
                    "purchase_orders.csv", "quality_inspections.csv"],
    }
    return {"datasets": [demo_entry] + list(_datasets.values())}


# --- Run analytics --------------------------------------------------------
@api_router.get("/analytics/{dataset_id}/summary")
async def analytics_summary(dataset_id: str):
    try:
        folder = _dataset_folder(dataset_id)
        return _compute(dataset_id, folder)
    except DataError as e:
        raise HTTPException(400, str(e))


# --- Upload a new dataset --------------------------------------------------
@api_router.post("/analytics/upload")
async def upload_dataset(
    vendors:             UploadFile = File(...),
    purchase_orders:     UploadFile = File(...),
    quality_inspections: UploadFile = File(...),
    products:            Optional[UploadFile] = File(None),
    name:                Optional[str] = Form(None),
):
    dataset_id = uuid.uuid4().hex[:12]
    folder = UPLOAD_ROOT / dataset_id
    folder.mkdir(parents=True, exist_ok=True)

    uploads: dict[str, UploadFile] = {
        "vendors":             vendors,
        "purchase_orders":     purchase_orders,
        "quality_inspections": quality_inspections,
    }
    if products is not None:
        uploads["products"] = products

    written: list[str] = []
    for key, f in uploads.items():
        dst = folder / f"{key}.csv"
        with dst.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        written.append(f"{key}.csv")

    # Try computing straight away so bad uploads fail loudly here
    try:
        summary = _compute(dataset_id, folder)
    except DataError as e:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(400, f"analytics failed on upload: {e}")
    except Exception as e:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(400, f"could not compute analytics: {e}")

    entry = {
        "id":         dataset_id,
        "name":       name or f"Uploaded dataset {dataset_id[:6]}",
        "source":     "upload",
        "files":      written,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "totals":     summary["totals"],
    }
    _datasets[dataset_id] = entry
    return entry


@api_router.delete("/analytics/{dataset_id}")
async def delete_dataset(dataset_id: str):
    if dataset_id == "demo":
        raise HTTPException(400, "cannot delete the demo dataset")
    if dataset_id not in _datasets:
        raise HTTPException(404, "dataset not found")
    folder = UPLOAD_ROOT / dataset_id
    shutil.rmtree(folder, ignore_errors=True)
    _summary_cache.pop(dataset_id, None)
    _datasets.pop(dataset_id, None)
    return {"deleted": dataset_id}


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
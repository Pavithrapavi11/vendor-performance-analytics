"""
NorthBridge Vendor Performance — analytics engine.

Pure functions over pandas DataFrames. Mirrors the SQL/Notebook methodology
exactly:
  * On-Time Delivery %, Defect Rate %, Price Variance %, Lead Time, Fill Rate %
  * Composite Vendor Score  = 0.40·OTD + 0.40·(100−Defect) + 0.20·(100−max(0,PriceVar))
  * Eligibility  ≥ 20 POs
  * PIP shortlist: bottom-3 by score AND (below-avg OTD OR above-avg defect)
                   walking down if a candidate has no operational issue
  * Reward shortlist: top-3 eligible by score
"""
from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Expected schema (used both for validation and for UI hints)
# ---------------------------------------------------------------------------
SCHEMA: dict[str, list[str]] = {
    "vendors": [
        "vendor_id", "vendor_name", "region", "vendor_category",
        "contract_start_date", "payment_terms",
    ],
    "products": [
        "product_id", "product_name", "category", "standard_unit_price",
    ],
    "purchase_orders": [
        "po_number", "vendor_id", "product_id", "order_date", "promised_date",
        "actual_delivery_date", "quantity_ordered", "quantity_received",
        "unit_price", "agreed_price", "invoice_amount", "order_status",
    ],
    "quality_inspections": [
        "inspection_id", "po_number", "inspection_date", "inspected_quantity",
        "defect_count", "complaint_count", "quality_status",
    ],
}


class DataError(Exception):
    """Raised when uploaded data can't be parsed / doesn't fit the schema."""


# ---------------------------------------------------------------------------
# 1. Load + validate + clean
# ---------------------------------------------------------------------------
def _require(df: pd.DataFrame, name: str, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise DataError(f"{name}.csv missing columns: {missing}")


def clean(
    vendors: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    quality_inspections: pd.DataFrame,
    products: pd.DataFrame | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, int]]:
    """Apply the same 6 cleaning decisions as the notebook.

    Returns (cleaned_frames, decision_log).
    """
    _require(vendors,             "vendors",             SCHEMA["vendors"])
    _require(purchase_orders,     "purchase_orders",     SCHEMA["purchase_orders"])
    _require(quality_inspections, "quality_inspections", SCHEMA["quality_inspections"])
    if products is not None:
        _require(products,        "products",            SCHEMA["products"])
    else:
        products = pd.DataFrame(columns=SCHEMA["products"])

    v  = vendors.copy()
    p  = products.copy()
    po = purchase_orders.copy()
    qi = quality_inspections.copy()

    log: dict[str, int] = {}

    # 1. Vendor-name casing
    normalised = v["vendor_name"].astype(str).str.strip().str.title()
    log["vendor_name_casing_fixed"] = int((v["vendor_name"] != normalised).sum())
    v["vendor_name"] = normalised

    # 2. Duplicate POs
    dup_mask = po.duplicated(subset="po_number", keep="first")
    log["duplicate_pos_dropped"] = int(dup_mask.sum())
    po = po.loc[~dup_mask].copy()

    # 3. Coerce dates
    for col in ("order_date", "promised_date", "actual_delivery_date"):
        po[col] = pd.to_datetime(po[col], errors="coerce")
    qi["inspection_date"] = pd.to_datetime(qi["inspection_date"], errors="coerce")

    # 4. Coerce numerics
    for col in ("quantity_ordered", "quantity_received"):
        po[col] = pd.to_numeric(po[col], errors="coerce")
    for col in ("unit_price", "agreed_price", "invoice_amount"):
        po[col] = pd.to_numeric(po[col], errors="coerce")
    for col in ("inspected_quantity", "defect_count", "complaint_count"):
        qi[col] = pd.to_numeric(qi[col], errors="coerce")

    log["missing_actual_delivery"] = int(po["actual_delivery_date"].isna().sum())
    log["agreed_price_zero_or_null"] = int(
        ((po["agreed_price"].isna()) | (po["agreed_price"] == 0)).sum()
    )
    log["overshipments_flagged"] = int(
        (po["quantity_received"] > po["quantity_ordered"]).sum()
    )

    # 5. Missing defect_count: fill 0 only when quality_status == 'Passed'
    missing_defect = qi["defect_count"].isna()
    fill_zero = missing_defect & (qi["quality_status"].astype(str) == "Passed")
    qi.loc[fill_zero, "defect_count"] = 0
    log["defect_count_filled_zero"] = int(fill_zero.sum())
    log["defect_count_still_missing"] = int(qi["defect_count"].isna().sum())

    return (
        {"vendors": v, "products": p,
         "purchase_orders": po, "quality_inspections": qi},
        log,
    )


# ---------------------------------------------------------------------------
# 2. Per-vendor KPI computation
# ---------------------------------------------------------------------------
def vendor_kpis(
    vendors: pd.DataFrame,
    po: pd.DataFrame,
    qi: pd.DataFrame,
) -> pd.DataFrame:
    """One row per vendor with every KPI defined in the report."""
    po = po.copy()
    qi_merged = qi.merge(
        po[["po_number", "vendor_id", "order_date"]], on="po_number", how="left"
    )

    # PO-level derived fields
    delivered_mask = po["actual_delivery_date"].notna()
    on_time_mask   = delivered_mask & (
        po["actual_delivery_date"] <= po["promised_date"]
    )
    po["_delivered"] = delivered_mask.astype(int)
    po["_on_time"]   = on_time_mask.astype(int)
    po["_lead_days"] = (po["actual_delivery_date"] - po["order_date"]).dt.days
    po["_fill_pct"]  = np.minimum(
        100.0,
        100.0 * po["quantity_received"].astype(float)
        / po["quantity_ordered"].replace(0, np.nan),
    )
    valid_agreed = po["agreed_price"].fillna(0) > 0
    po["_price_var_pct"] = np.where(
        valid_agreed,
        100.0 * (po["unit_price"] - po["agreed_price"]) / po["agreed_price"],
        np.nan,
    )

    po_grp = po.groupby("vendor_id", dropna=False)
    po_stats = pd.DataFrame({
        "total_pos":       po_grp.size(),
        "total_spend_inr": po_grp["invoice_amount"].sum(min_count=1),
        "delivered":       po_grp["_delivered"].sum(),
        "on_time":         po_grp["_on_time"].sum(),
        "avg_lead_days":   po_grp["_lead_days"].mean(),
        "avg_fill_rate":   po.loc[po["order_status"].astype(str) != "Cancelled"]
                             .groupby("vendor_id")["_fill_pct"].mean(),
        "avg_price_var":   po_grp["_price_var_pct"].mean(),
    }).reset_index()

    # Quality-inspection aggregations
    qi_grp = qi_merged.groupby("vendor_id", dropna=False)
    qi_stats = pd.DataFrame({
        "inspected_pos":       qi_grp.size(),
        "total_inspected_qty": qi_grp["inspected_quantity"].sum(min_count=1),
        "total_defects":       qi_grp["defect_count"].sum(min_count=1),
    }).reset_index()
    qi_stats["defect_rate_pct"] = np.where(
        qi_stats["total_inspected_qty"].fillna(0) > 0,
        100.0 * qi_stats["total_defects"] / qi_stats["total_inspected_qty"],
        np.nan,
    )

    out = vendors.merge(po_stats, on="vendor_id", how="left") \
                 .merge(qi_stats, on="vendor_id", how="left")

    out["otd_pct"] = np.where(
        out["delivered"].fillna(0) > 0,
        100.0 * out["on_time"] / out["delivered"],
        np.nan,
    )
    out["inspection_coverage_pct"] = np.where(
        out["total_pos"].fillna(0) > 0,
        100.0 * out["inspected_pos"].fillna(0) / out["total_pos"],
        np.nan,
    )
    # Composite (safe against nulls)
    otd_safe    = out["otd_pct"].fillna(0)
    defect_safe = out["defect_rate_pct"].fillna(0)
    price_safe  = out["avg_price_var"].fillna(0).clip(lower=0)
    out["composite_score"] = (
        0.40 * otd_safe
        + 0.40 * (100.0 - defect_safe)
        + 0.20 * (100.0 - price_safe)
    )
    return out


# ---------------------------------------------------------------------------
# 3. PIP + Reward selection
# ---------------------------------------------------------------------------
def select_pip_reward(vendor_kpi: pd.DataFrame,
                      min_pos: int = 20) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    eligible = vendor_kpi[vendor_kpi["total_pos"].fillna(0) >= min_pos].copy()
    if eligible.empty:
        return eligible.head(0), eligible.head(0), {"avg_otd": None, "avg_defect": None}

    avg_otd    = float(eligible["otd_pct"].mean(skipna=True))
    avg_defect = float(eligible["defect_rate_pct"].mean(skipna=True))
    benchmarks = {"avg_otd": round(avg_otd, 2), "avg_defect": round(avg_defect, 2)}

    eligible["has_issue"] = (
        (eligible["otd_pct"] < avg_otd) |
        (eligible["defect_rate_pct"] > avg_defect)
    )

    # PIP: walk down score-ascending, take first 3 that have an issue
    pip = (
        eligible.sort_values("composite_score", ascending=True)
                .loc[lambda d: d["has_issue"]]
                .head(3)
                .copy()
    )
    pip["benchmark_otd"]    = avg_otd
    pip["benchmark_defect"] = avg_defect

    reward = eligible.sort_values("composite_score", ascending=False).head(3).copy()

    return pip, reward, benchmarks


# ---------------------------------------------------------------------------
# 4. Trend / category helpers used by the dashboard
# ---------------------------------------------------------------------------
def monthly_trends(vendors: pd.DataFrame,
                   po: pd.DataFrame,
                   qi: pd.DataFrame) -> pd.DataFrame:
    """Monthly OTD % and defect % per vendor (and one 'ALL' row)."""
    po = po.copy()
    po["month"] = po["order_date"].dt.to_period("M").dt.to_timestamp()
    qi_j = qi.merge(po[["po_number", "vendor_id", "month"]],
                    on="po_number", how="left")

    delivered = po["actual_delivery_date"].notna()
    on_time   = delivered & (po["actual_delivery_date"] <= po["promised_date"])
    po["_delivered"] = delivered.astype(int)
    po["_on_time"]   = on_time.astype(int)

    per_v = po.groupby(["vendor_id", "month"]).agg(
        po_count=("po_number", "count"),
        delivered=("_delivered", "sum"),
        on_time=("_on_time", "sum"),
    ).reset_index()
    q_per_v = qi_j.groupby(["vendor_id", "month"]).agg(
        inspected_qty=("inspected_quantity", "sum"),
        defects=("defect_count", "sum"),
    ).reset_index()
    m = per_v.merge(q_per_v, on=["vendor_id", "month"], how="left")
    m["otd_pct"] = np.where(
        m["delivered"] > 0, 100.0 * m["on_time"] / m["delivered"], np.nan
    )
    m["defect_rate_pct"] = np.where(
        m["inspected_qty"].fillna(0) > 0,
        100.0 * m["defects"] / m["inspected_qty"], np.nan,
    )
    m = m.merge(vendors[["vendor_id", "vendor_name"]], on="vendor_id", how="left")

    # Overall (all vendors) monthly average
    overall = po.groupby("month").agg(
        delivered=("_delivered", "sum"),
        on_time=("_on_time", "sum"),
    ).reset_index()
    overall_q = qi_j.groupby("month").agg(
        inspected_qty=("inspected_quantity", "sum"),
        defects=("defect_count", "sum"),
    ).reset_index()
    o = overall.merge(overall_q, on="month", how="left")
    o["otd_pct"] = np.where(o["delivered"] > 0,
                             100.0 * o["on_time"] / o["delivered"], np.nan)
    o["defect_rate_pct"] = np.where(o["inspected_qty"].fillna(0) > 0,
                                     100.0 * o["defects"] / o["inspected_qty"], np.nan)
    o["vendor_id"]   = "__ALL__"
    o["vendor_name"] = "All vendors"
    o["po_count"]    = po.groupby("month").size().values

    return pd.concat([m, o[m.columns]], ignore_index=True)


def category_analysis(vendors: pd.DataFrame,
                      po: pd.DataFrame,
                      qi: pd.DataFrame) -> pd.DataFrame:
    po = po.merge(vendors[["vendor_id", "vendor_category"]],
                  on="vendor_id", how="left")
    qi_j = qi.merge(po[["po_number", "vendor_category"]],
                    on="po_number", how="left")

    delivered = po["actual_delivery_date"].notna()
    on_time   = delivered & (po["actual_delivery_date"] <= po["promised_date"])
    po["_delivered"] = delivered.astype(int)
    po["_on_time"]   = on_time.astype(int)
    valid_ap = po["agreed_price"].fillna(0) > 0
    po["_pv"] = np.where(valid_ap,
                          100.0 * (po["unit_price"] - po["agreed_price"])
                          / po["agreed_price"], np.nan)

    g = po.groupby("vendor_category").agg(
        vendors=("vendor_id", "nunique"),
        total_pos=("po_number", "count"),
        total_spend=("invoice_amount", "sum"),
        delivered=("_delivered", "sum"),
        on_time=("_on_time", "sum"),
        avg_price_var_pct=("_pv", "mean"),
    ).reset_index()
    qg = qi_j.groupby("vendor_category").agg(
        insp_qty=("inspected_quantity", "sum"),
        defects=("defect_count", "sum"),
    ).reset_index()
    out = g.merge(qg, on="vendor_category", how="left")
    out["otd_pct"] = np.where(out["delivered"] > 0,
                               100.0 * out["on_time"] / out["delivered"], np.nan)
    out["defect_rate_pct"] = np.where(out["insp_qty"].fillna(0) > 0,
                                       100.0 * out["defects"] / out["insp_qty"], np.nan)
    return out[["vendor_category", "vendors", "total_pos", "total_spend",
                "otd_pct", "defect_rate_pct", "avg_price_var_pct"]]


def delivery_buckets(po: pd.DataFrame) -> pd.DataFrame:
    po = po.copy()
    diff = (po["actual_delivery_date"] - po["promised_date"]).dt.days
    conditions = [
        po["actual_delivery_date"].isna(),
        diff <= 0,
        (diff >= 1) & (diff <= 3),
    ]
    po["bucket"] = np.select(conditions,
                              ["Unknown", "On Time", "Slightly Late"],
                              default="Significantly Late")
    grp = po.groupby(["vendor_id", "bucket"]).size().unstack(fill_value=0).reset_index()
    for c in ("On Time", "Slightly Late", "Significantly Late", "Unknown"):
        if c not in grp.columns:
            grp[c] = 0
    return grp[["vendor_id", "On Time", "Slightly Late", "Significantly Late", "Unknown"]]


def quality_decline(vendors: pd.DataFrame,
                    po: pd.DataFrame,
                    qi: pd.DataFrame,
                    cutoff_month: int = 4) -> pd.DataFrame:
    qi_j = qi.merge(po[["po_number", "vendor_id", "order_date"]],
                    on="po_number", how="left")
    qi_j["mon"] = qi_j["order_date"].dt.month
    pre  = qi_j[qi_j["mon"] <= cutoff_month]
    post = qi_j[qi_j["mon"]  > cutoff_month]

    def _agg(df):
        return df.groupby("vendor_id").agg(
            qty=("inspected_quantity", "sum"),
            defects=("defect_count", "sum"),
            n=("po_number", "count"),
        ).reset_index()

    a, b = _agg(pre), _agg(post)
    merged = a.merge(b, on="vendor_id", how="outer", suffixes=("_pre", "_post")).fillna(0)
    merged["pre_defect_pct"]  = np.where(merged["qty_pre"]  > 0,
                                          100.0 * merged["defects_pre"]  / merged["qty_pre"],  np.nan)
    merged["post_defect_pct"] = np.where(merged["qty_post"] > 0,
                                          100.0 * merged["defects_post"] / merged["qty_post"], np.nan)
    merged["delta_pct"] = merged["post_defect_pct"] - merged["pre_defect_pct"]
    merged = merged[(merged["n_pre"] >= 3) & (merged["n_post"] >= 3)]
    merged = merged.merge(vendors[["vendor_id", "vendor_name"]],
                          on="vendor_id", how="left")
    return merged.sort_values("delta_pct", ascending=False, na_position="last")


# ---------------------------------------------------------------------------
# 5. Orchestrator — produces one JSON-ready dict for the dashboard
# ---------------------------------------------------------------------------
def _clean_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame → list-of-dicts with JSON-safe values."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].round(4)
    df = df.replace({np.nan: None, pd.NA: None})
    return df.to_dict(orient="records")


def build_summary(vendors: pd.DataFrame,
                  po: pd.DataFrame,
                  qi: pd.DataFrame,
                  products: pd.DataFrame | None = None) -> dict:
    cleaned, log = clean(vendors, po, qi, products)
    v, p, po_c, qi_c = (cleaned["vendors"], cleaned["products"],
                        cleaned["purchase_orders"], cleaned["quality_inspections"])

    kpi = vendor_kpis(v, po_c, qi_c)
    pip, reward, bench = select_pip_reward(kpi)
    cat  = category_analysis(v, po_c, qi_c)
    monthly = monthly_trends(v, po_c, qi_c)
    buckets = delivery_buckets(po_c).merge(
        v[["vendor_id", "vendor_name"]], on="vendor_id", how="left"
    )
    decline = quality_decline(v, po_c, qi_c).head(5)

    kpi_view = kpi[[
        "vendor_id", "vendor_name", "region", "vendor_category",
        "total_pos", "total_spend_inr",
        "otd_pct", "defect_rate_pct", "avg_fill_rate", "avg_price_var",
        "avg_lead_days", "inspected_pos", "inspection_coverage_pct",
        "composite_score",
    ]].rename(columns={
        "avg_fill_rate":  "fill_rate_pct",
        "avg_price_var":  "price_var_pct",
    })

    pip_view = pip[[
        "vendor_id", "vendor_name", "vendor_category", "total_pos",
        "otd_pct", "defect_rate_pct", "avg_fill_rate", "avg_price_var",
        "composite_score", "benchmark_otd", "benchmark_defect",
    ]].rename(columns={"avg_fill_rate": "fill_rate_pct",
                        "avg_price_var": "price_var_pct"}) \
        if not pip.empty else pip
    reward_view = reward[[
        "vendor_id", "vendor_name", "vendor_category", "total_pos",
        "otd_pct", "defect_rate_pct", "avg_fill_rate", "avg_price_var",
        "composite_score",
    ]].rename(columns={"avg_fill_rate": "fill_rate_pct",
                        "avg_price_var": "price_var_pct"}) \
        if not reward.empty else reward

    return {
        "totals": {
            "total_pos":       int(len(po_c)),
            "unique_vendors":  int(v["vendor_id"].nunique()),
            "unique_products": int(p["product_id"].nunique()) if len(p) else None,
            "total_spend_inr": float(po_c["invoice_amount"].sum(skipna=True)),
            "earliest_order":  po_c["order_date"].min().strftime("%Y-%m-%d")
                               if po_c["order_date"].notna().any() else None,
            "latest_order":    po_c["order_date"].max().strftime("%Y-%m-%d")
                               if po_c["order_date"].notna().any() else None,
            "inspected_pos":   int(len(qi_c)),
            "inspection_coverage_pct":
                round(100.0 * len(qi_c) / max(1, len(po_c)), 2),
        },
        "averages": {
            "otd_pct":         round(float(kpi["otd_pct"].mean(skipna=True)), 2)
                               if kpi["otd_pct"].notna().any() else None,
            "defect_rate_pct": round(float(kpi["defect_rate_pct"].mean(skipna=True)), 2)
                               if kpi["defect_rate_pct"].notna().any() else None,
            "composite_score": round(float(kpi["composite_score"].mean(skipna=True)), 2),
        },
        "benchmarks":     bench,
        "cleaning_log":   log,
        "leaderboard":    _clean_records(kpi_view),
        "pip":            _clean_records(pip_view) if not pip.empty else [],
        "reward":         _clean_records(reward_view) if not reward.empty else [],
        "category":       _clean_records(cat),
        "monthly":        _clean_records(monthly),
        "delivery_buckets": _clean_records(buckets),
        "decline":        _clean_records(decline),
    }

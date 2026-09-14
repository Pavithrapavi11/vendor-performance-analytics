"""
NorthBridge Supplies — Synthetic Data Generator
================================================
Generates raw CSVs for the vendor performance analytics project.

Output (into ../data/raw/):
    vendors.csv, products.csv, purchase_orders.csv, quality_inspections.csv

Realism / intentional "dirt" injected:
    * 1 vendor's quality declines after month 4
    * ~55–65% of POs get an inspection record (subset-inspection reality)
    * ~2% of inspected rows have missing defect_count
    * ~10 duplicate PO rows
    * Inconsistent casing on 2 vendor names
    * ~1% missing actual_delivery_date
    * A few rows with quantity_received > quantity_ordered
    * Uneven order volumes across vendors
    * One seasonal dip in month 7 (July)
"""

import os
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_IN")
Faker.seed(SEED)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #
REGIONS = ["North", "South", "East", "West"]
CATEGORIES = ["Packaging", "Raw Materials", "Logistics", "MRO"]
PAYMENT_TERMS = ["Net 30", "Net 45", "Net 60"]

VENDOR_NAMES = [
    "Bharat Packaging Co", "Ganga Industries", "Krishna Traders", "Meghna Supplies",
    "Sundar Logistics", "Ravi Raw Materials", "Vikram Enterprises", "Aditya Corp",
    "Sagar Packworks", "Himalaya MRO", "Chennai Freight Ltd", "Kolkata Rawmet",
    "Deccan Distributors", "Ashoka Papers", "Nilgiri Metals", "Konark Cargo",
    "Godavari Supplies", "Yamuna Packaging", "Narmada Traders", "Kaveri Movers",
]

PRODUCTS_BY_CATEGORY = {
    "Packaging":     [("Corrugated Box 12x8", 45), ("Plastic Film Roll", 320),
                      ("Bubble Wrap 100m",  180), ("Stretch Wrap Roll", 260)],
    "Raw Materials": [("Steel Sheet 2mm",  1200), ("Aluminium Coil",   2100),
                      ("Copper Wire kg",    780), ("MS Rod 10mm",       410)],
    "Logistics":     [("Freight FTL Delhi", 42000), ("Freight FTL Mumbai", 38000),
                      ("LTL Consolidation",  8500), ("Last-Mile Delivery",  650)],
    "MRO":           [("Lubricant 5L",       850), ("Safety Gloves Pack", 320),
                      ("Bearing 6205",       210), ("Industrial Sealant", 480)],
}

# --------------------------------------------------------------------------- #
# 1. Vendors
# --------------------------------------------------------------------------- #
vendors = []
for i, name in enumerate(VENDOR_NAMES, start=1):
    vendors.append({
        "vendor_id":           f"V{i:03d}",
        "vendor_name":         name,
        "region":              random.choice(REGIONS),
        "vendor_category":     random.choice(CATEGORIES),
        "contract_start_date": fake.date_between(start_date=date(2021, 1, 1),
                                                 end_date=date(2023, 6, 30)),
        "payment_terms":       random.choice(PAYMENT_TERMS),
    })

# Inject inconsistent casing on two vendor names (dirt)
vendors[2]["vendor_name"] = vendors[2]["vendor_name"].upper()
vendors[7]["vendor_name"] = vendors[7]["vendor_name"].lower()

vendors_df = pd.DataFrame(vendors)

# --------------------------------------------------------------------------- #
# 2. Products
# --------------------------------------------------------------------------- #
products = []
pid = 1
for cat, items in PRODUCTS_BY_CATEGORY.items():
    for pname, price in items:
        products.append({
            "product_id":          f"P{pid:03d}",
            "product_name":        pname,
            "category":            cat,
            "standard_unit_price": price,
        })
        pid += 1
products_df = pd.DataFrame(products)

# --------------------------------------------------------------------------- #
# 3. Purchase Orders (fact)
# --------------------------------------------------------------------------- #
# Uneven vendor volumes: some heavy suppliers, some light
volume_weights = np.array([
    140, 120, 110, 100, 95, 85, 80, 75, 70, 65,
     60, 55, 50, 45, 40, 35, 30, 25, 20, 15,
], dtype=float)
np.random.shuffle(volume_weights)
volume_weights = volume_weights / volume_weights.sum()

TOTAL_POS = 1400
vendor_po_counts = np.random.multinomial(TOTAL_POS, volume_weights)

# Pick one vendor (index 4) whose quality declines after month 4
DECLINE_VENDOR_IDX = 4
DECLINE_VENDOR_ID  = vendors[DECLINE_VENDOR_IDX]["vendor_id"]

pos = []
po_counter = 1
for v_idx, vendor in enumerate(vendors):
    n = vendor_po_counts[v_idx]
    for _ in range(n):
        # Order date across Jan–Sep with a dip in July
        month = np.random.choice(
            range(1, 10),
            p=[0.12, 0.12, 0.12, 0.13, 0.12, 0.11, 0.06, 0.11, 0.11]  # July dip
        )
        day = random.randint(1, 28)
        order_date = date(2025, month, day)

        # Category-driven product selection when vendor has a category
        cat_products = products_df[products_df["category"] == vendor["vendor_category"]]
        if len(cat_products) and random.random() < 0.75:
            prod = cat_products.sample(1).iloc[0]
        else:
            prod = products_df.sample(1).iloc[0]

        agreed_price = float(prod["standard_unit_price"])
        # Price variance: +/- ~5% typically, some vendors run hotter
        variance_pct = np.random.normal(loc=0.02, scale=0.05)
        unit_price = round(agreed_price * (1 + variance_pct), 2)

        # Promised lead time — vendor category driven
        promised_lead = {
            "Logistics":     random.randint(2, 6),
            "Packaging":     random.randint(5, 12),
            "MRO":           random.randint(4, 10),
            "Raw Materials": random.randint(7, 18),
        }[vendor["vendor_category"]]
        promised_date = order_date + timedelta(days=promised_lead)

        # Actual delivery: some vendors are chronically late (idx 1, 9, 13)
        base_delay = np.random.normal(0, 1.5)
        if v_idx in (1, 9, 13):
            base_delay += np.random.normal(3, 2)
        actual_delivery_date = promised_date + timedelta(days=int(round(base_delay)))

        # Quantity
        quantity_ordered  = random.choice([10, 20, 25, 50, 100, 200, 500])
        # Fill rate: mostly full, sometimes short, rarely over
        fill_pct = np.clip(np.random.normal(0.98, 0.06), 0.6, 1.05)
        quantity_received = int(round(quantity_ordered * fill_pct))

        # Order status
        if quantity_received == 0:
            status = "Cancelled"
        elif quantity_received < quantity_ordered * 0.95:
            status = "Partial"
        else:
            status = "Delivered"

        invoice_amount = round(unit_price * quantity_received, 2)

        pos.append({
            "po_number":            f"PO{po_counter:05d}",
            "vendor_id":            vendor["vendor_id"],
            "product_id":           prod["product_id"],
            "order_date":           order_date,
            "promised_date":        promised_date,
            "actual_delivery_date": actual_delivery_date,
            "quantity_ordered":     quantity_ordered,
            "quantity_received":    quantity_received,
            "unit_price":           unit_price,
            "agreed_price":         agreed_price,
            "invoice_amount":       invoice_amount,
            "order_status":         status,
        })
        po_counter += 1

po_df = pd.DataFrame(pos)

# ---- Inject dirtiness -------------------------------------------------------

# ~1% of actual_delivery_date -> NULL
null_mask = np.random.rand(len(po_df)) < 0.01
po_df.loc[null_mask, "actual_delivery_date"] = pd.NaT

# ~0.5% of agreed_price -> 0 (dirty)
zero_mask = np.random.rand(len(po_df)) < 0.005
po_df.loc[zero_mask, "agreed_price"] = 0

# Duplicate ~10 PO rows verbatim (they will keep the same po_number so cleaning
# will drop them). This mimics accidental double-entry in an ERP.
duplicates = po_df.sample(10, random_state=SEED)
po_df = pd.concat([po_df, duplicates], ignore_index=True)

# --------------------------------------------------------------------------- #
# 4. Quality Inspections — only ~55–65% of POs get inspected
# --------------------------------------------------------------------------- #
unique_pos = po_df.drop_duplicates(subset="po_number")
inspection_rate = 0.60
inspected = unique_pos.sample(frac=inspection_rate, random_state=SEED)

qi_rows = []
for i, row in enumerate(inspected.itertuples(index=False), start=1):
    # Quality decline: for DECLINE_VENDOR after month 4, defect rate jumps
    is_decline_vendor = (row.vendor_id == DECLINE_VENDOR_ID)
    month = row.order_date.month
    if is_decline_vendor and month > 4:
        defect_rate = np.random.uniform(0.08, 0.15)
    else:
        # Vendor-specific baseline
        seed_val = int(row.vendor_id[1:]) * 7
        rng = np.random.default_rng(seed_val + i)
        defect_rate = max(0, rng.normal(0.02, 0.015))

        # A couple of vendors have chronically higher defects
        if row.vendor_id in ("V011", "V017"):
            defect_rate += 0.03

    inspected_qty = max(1, int(row.quantity_received * random.uniform(0.7, 1.0)))
    defect_count  = int(round(inspected_qty * defect_rate))

    if defect_count == 0:
        status = "Passed"
    elif defect_rate < 0.05:
        status = "Conditional"
    else:
        status = "Failed"

    qi_rows.append({
        "inspection_id":      f"QI{i:05d}",
        "po_number":          row.po_number,
        "inspection_date":    row.actual_delivery_date if pd.notna(row.actual_delivery_date)
                              else row.promised_date,
        "inspected_quantity": inspected_qty,
        "defect_count":       defect_count,
        "complaint_count":    int(defect_count > 0) * random.randint(0, 2),
        "quality_status":     status,
    })

qi_df = pd.DataFrame(qi_rows)

# ~2% of defect_count -> NaN (dirty)
missing_defect = np.random.rand(len(qi_df)) < 0.02
qi_df.loc[missing_defect, "defect_count"] = np.nan

# --------------------------------------------------------------------------- #
# Save
# --------------------------------------------------------------------------- #
vendors_df.to_csv(OUT_DIR / "vendors.csv",             index=False)
products_df.to_csv(OUT_DIR / "products.csv",           index=False)
po_df.to_csv(     OUT_DIR / "purchase_orders.csv",     index=False)
qi_df.to_csv(     OUT_DIR / "quality_inspections.csv", index=False)

print(f"Vendors:              {len(vendors_df):>5}")
print(f"Products:             {len(products_df):>5}")
print(f"Purchase Orders:      {len(po_df):>5}  (incl. {len(po_df) - len(unique_pos)} duplicates)")
print(f"Unique POs:           {len(unique_pos):>5}")
print(f"Quality Inspections:  {len(qi_df):>5}  ({100*len(qi_df)/len(unique_pos):.1f}% coverage)")
print(f"Saved to:             {OUT_DIR}")

"""
Generate all Matplotlib charts used in the notebooks, PDF report, and
Power BI dashboard mockups.  Output: /report/figures/*.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIG  = ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
SQL  = ROOT / "data" / "sql_outputs"
CLEAN = ROOT / "data" / "clean"

plt.rcParams.update({
    "figure.dpi":      110,
    "font.family":     "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
    "axes.titlesize":  12,
})

NB_TEAL   = "#0E7C86"
NB_CORAL  = "#E76F51"
NB_SAND   = "#E9C46A"
NB_INK    = "#1D3557"
NB_GREY   = "#B0B0B0"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {name}")


# --------------------------------------------------------------------------- #
# 1. Order volume by vendor (bar)
# --------------------------------------------------------------------------- #
po = pd.read_csv(CLEAN / "purchase_orders_clean.csv")
v  = pd.read_csv(CLEAN / "vendors_clean.csv")
volumes = po.groupby("vendor_id").size().reset_index(name="pos") \
            .merge(v[["vendor_id", "vendor_name"]], on="vendor_id") \
            .sort_values("pos", ascending=True)

fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(volumes["vendor_name"], volumes["pos"], color=NB_TEAL)
ax.set_title("Purchase-order volume by vendor (Jan–Sep 2025)")
ax.set_xlabel("Number of POs")
save(fig, "01_order_volume_by_vendor.png")

# --------------------------------------------------------------------------- #
# 2. Monthly OTD trend (all vendors avg) + decline vendor overlay
# --------------------------------------------------------------------------- #
monthly = pd.read_csv(SQL / "03_monthly_trends__q1.csv", parse_dates=["month"])
overall = monthly.groupby("month")["otd_pct"].mean().reset_index()
v005    = monthly[monthly["vendor_id"] == "V005"]

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(overall["month"], overall["otd_pct"], marker="o",
        color=NB_INK, linewidth=2, label="All-vendor avg")
ax.plot(v005["month"], v005["otd_pct"], marker="s",
        color=NB_CORAL, linewidth=2, label="V005 Sundar Logistics")
ax.axvline(pd.Timestamp("2025-05-01"), color=NB_GREY, linestyle="--",
           alpha=0.7, label="Month-4 cutoff")
ax.set_title("Monthly on-time delivery %")
ax.set_ylabel("OTD %"); ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.set_xlabel("Month"); ax.legend(loc="lower left")
save(fig, "02_monthly_otd_trend.png")

# --------------------------------------------------------------------------- #
# 3. Defect distribution (inspected POs only)
# --------------------------------------------------------------------------- #
qi = pd.read_csv(CLEAN / "quality_inspections_clean.csv")
qi = qi.dropna(subset=["defect_count"])
defect_rate = 100 * qi["defect_count"] / qi["inspected_quantity"]

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(defect_rate, bins=30, color=NB_TEAL, edgecolor="white")
ax.set_title("Distribution of PO-level defect rate (inspected POs)")
ax.set_xlabel("Defect rate %"); ax.set_ylabel("Number of inspected POs")
save(fig, "03_defect_distribution.png")

# --------------------------------------------------------------------------- #
# 4. Delivery delay histogram
# --------------------------------------------------------------------------- #
po_dates = po.dropna(subset=["actual_delivery_date"]).copy()
po_dates["delay"] = (pd.to_datetime(po_dates["actual_delivery_date"]) -
                     pd.to_datetime(po_dates["promised_date"])).dt.days

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(po_dates["delay"], bins=30, color=NB_CORAL, edgecolor="white")
ax.axvline(0, color=NB_INK, linestyle="--")
ax.set_title("Delivery-delay distribution (days after promised date)")
ax.set_xlabel("Delay (days)  ← early | late →")
ax.set_ylabel("Number of POs")
save(fig, "04_delivery_delay_hist.png")

# --------------------------------------------------------------------------- #
# 5. Price variance by category (box)
# --------------------------------------------------------------------------- #
merged = po.merge(v[["vendor_id", "vendor_category"]], on="vendor_id")
merged = merged[merged["agreed_price"] > 0].copy()
merged["variance_pct"] = 100 * (merged["unit_price"] - merged["agreed_price"]) / merged["agreed_price"]
cats = merged["vendor_category"].unique()
data = [merged.loc[merged["vendor_category"] == c, "variance_pct"].values for c in cats]

fig, ax = plt.subplots(figsize=(8, 4.5))
bp = ax.boxplot(data, tick_labels=cats, patch_artist=True)
for patch in bp["boxes"]:
    patch.set_facecolor(NB_SAND); patch.set_edgecolor(NB_INK)
ax.set_title("Price variance % by vendor category")
ax.set_ylabel("Price variance %")
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
save(fig, "05_price_variance_by_category.png")

# --------------------------------------------------------------------------- #
# 6. Vendor leaderboard (composite score horizontal bar)
# --------------------------------------------------------------------------- #
lb = pd.read_csv(SQL / "09_pip_candidates__q1.csv").sort_values("composite_score")
pip_ids    = pd.read_csv(SQL / "09_pip_candidates__q2.csv")["vendor_id"].tolist()
reward_ids = pd.read_csv(SQL / "09_pip_candidates__q3.csv")["vendor_id"].tolist()
colors = [NB_CORAL if vid in pip_ids else NB_TEAL if vid in reward_ids else NB_GREY
          for vid in lb["vendor_id"]]

fig, ax = plt.subplots(figsize=(9, 6.5))
ax.barh(lb["vendor_name"], lb["composite_score"], color=colors)
for i, (score, vid) in enumerate(zip(lb["composite_score"], lb["vendor_id"])):
    tag = " PIP" if vid in pip_ids else (" ★" if vid in reward_ids else "")
    ax.text(score + 0.3, i, f"{score:.1f}{tag}", va="center", fontsize=8)
ax.set_title("Vendor leaderboard — composite score (higher is better)")
ax.set_xlabel("Composite score")
ax.set_xlim(60, 95)
save(fig, "06_vendor_leaderboard.png")

# --------------------------------------------------------------------------- #
# 7. Category heatmap (OTD % and defect % side-by-side)
# --------------------------------------------------------------------------- #
cat = pd.read_csv(SQL / "04_category_analysis__q1.csv")
fig, ax = plt.subplots(figsize=(7, 3.5))
mat = cat[["otd_pct", "defect_rate_pct"]].values.T
im = ax.imshow(mat, cmap="RdYlGn", aspect="auto",
               vmin=0, vmax=max(cat["otd_pct"].max(), 100))
ax.set_yticks([0, 1]); ax.set_yticklabels(["OTD %", "Defect %"])
ax.set_xticks(range(len(cat))); ax.set_xticklabels(cat["vendor_category"], rotation=15)
for i in range(2):
    for j in range(len(cat)):
        ax.text(j, i, f"{mat[i, j]:.1f}", ha="center", va="center",
                color="black", fontsize=10)
ax.set_title("Category heatmap: OTD % and defect %")
save(fig, "07_category_heatmap.png")

# --------------------------------------------------------------------------- #
# 8. Delivery buckets (stacked bar for PIP + reward vendors)
# --------------------------------------------------------------------------- #
buck = pd.read_csv(SQL / "05_delivery_buckets__q1.csv")
show = buck[buck["vendor_id"].isin(pip_ids + reward_ids)].copy()
show = show.sort_values("otd_pct")
fig, ax = plt.subplots(figsize=(9, 4.5))
bottom = np.zeros(len(show))
for col, color, label in [
    ("on_time",             NB_TEAL, "On time"),
    ("slightly_late",       NB_SAND, "Slightly late (1–3d)"),
    ("significantly_late",  NB_CORAL, "Significantly late (>3d)"),
]:
    ax.bar(show["vendor_name"], show[col], bottom=bottom, color=color, label=label)
    bottom += show[col].values
ax.set_title("Delivery buckets — PIP candidates vs reward candidates")
ax.set_ylabel("Number of POs")
ax.tick_params(axis="x", rotation=30)
ax.legend()
save(fig, "08_delivery_buckets.png")

# --------------------------------------------------------------------------- #
# 9. Inspection coverage per vendor
# --------------------------------------------------------------------------- #
cov = pd.read_csv(SQL / "02_vendor_level__q1.csv").sort_values("inspection_coverage_pct")
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(cov["vendor_name"], cov["inspection_coverage_pct"], color=NB_INK)
ax.set_title("Quality-inspection coverage % per vendor")
ax.set_xlabel("Inspected POs / total POs")
ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
save(fig, "09_inspection_coverage.png")

# --------------------------------------------------------------------------- #
# 10. ER diagram (drawn with matplotlib — no graphviz dep)
# --------------------------------------------------------------------------- #
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.axis("off")

def box(x, y, w, h, title, cols, color):
    ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=color, edgecolor=NB_INK, lw=1.4))
    ax.text(x + w/2, y + h - 0.3, title, ha="center", va="top",
            fontsize=11, fontweight="bold", color="white")
    for i, c in enumerate(cols):
        ax.text(x + 0.15, y + h - 0.75 - i*0.32, c, ha="left", va="top",
                fontsize=8.5, family="monospace")

box(0.5, 3.5, 2.6, 3.0, "vendors",
    ["PK vendor_id", "vendor_name", "region",
     "vendor_category", "contract_start_date", "payment_terms"], NB_TEAL)

box(4.2, 3.5, 2.6, 3.5, "purchase_orders (fact)",
    ["PK po_number", "FK vendor_id", "FK product_id",
     "order_date", "promised_date", "actual_delivery_date",
     "quantity_ordered", "quantity_received",
     "unit_price", "agreed_price",
     "invoice_amount", "order_status"], NB_INK)

box(7.9, 3.5, 2.6, 3.0, "products",
    ["PK product_id", "product_name",
     "category", "standard_unit_price"], NB_TEAL)

box(4.2, 0.2, 2.6, 2.6, "quality_inspections",
    ["PK inspection_id", "FK po_number (UNIQUE)",
     "inspection_date", "inspected_quantity",
     "defect_count", "complaint_count",
     "quality_status"], NB_CORAL)

# arrows
ax.annotate("", xy=(4.2, 5.0), xytext=(3.1, 5.0),
            arrowprops=dict(arrowstyle="->", lw=1.6, color=NB_INK))
ax.annotate("", xy=(7.9, 5.0), xytext=(6.8, 5.0),
            arrowprops=dict(arrowstyle="<-", lw=1.6, color=NB_INK))
ax.annotate("", xy=(5.5, 2.8), xytext=(5.5, 3.5),
            arrowprops=dict(arrowstyle="<-", lw=1.6, color=NB_INK))
ax.text(3.6, 5.15, "1  N", fontsize=8, color=NB_INK)
ax.text(7.3, 5.15, "N  1", fontsize=8, color=NB_INK)
ax.text(5.6, 3.15, "1 (optional)", fontsize=8, color=NB_INK)

ax.set_xlim(0, 11); ax.set_ylim(0, 7)
ax.set_title("NorthBridge Supplies — ER diagram", fontsize=13, fontweight="bold")
save(fig, "10_er_diagram.png")

# Also copy ER diagram to /report/ directly with expected name
import shutil
shutil.copy(FIG / "10_er_diagram.png", ROOT / "report" / "er_diagram.png")

# --------------------------------------------------------------------------- #
# 11. Dashboard mockups — Executive Summary
# --------------------------------------------------------------------------- #
fig = plt.figure(figsize=(14, 8))
fig.suptitle("Power BI — Page 1: Executive Summary (mockup)",
             fontsize=15, fontweight="bold", y=0.995)

# KPI cards
ax_cards = fig.add_axes([0.03, 0.78, 0.94, 0.16]); ax_cards.axis("off")
kpi_q1 = pd.read_csv(SQL / "01_basic_kpis__q1.csv").iloc[0]
lb_all = pd.read_csv(SQL / "09_pip_candidates__q1.csv")
cards = [
    ("Total POs",           f"{int(kpi_q1['total_pos']):,}",              NB_TEAL),
    ("Total spend",         f"₹{kpi_q1['total_spend_inr']/1e7:.2f} Cr",   NB_INK),
    ("Avg OTD %",           f"{lb_all['otd_pct'].mean():.1f}%",            NB_TEAL),
    ("Avg defect rate",     f"{lb_all['defect_rate_pct'].mean():.2f}%",   NB_CORAL),
    ("Avg vendor score",    f"{lb_all['composite_score'].mean():.1f}",    NB_SAND),
]
for i, (label, val, col) in enumerate(cards):
    x = 0.005 + i * 0.199
    ax_cards.add_patch(plt.Rectangle((x, 0), 0.19, 1, facecolor=col, alpha=0.9,
                                     transform=ax_cards.transAxes))
    ax_cards.text(x + 0.095, 0.62, val, ha="center", va="center",
                  fontsize=17, fontweight="bold", color="white",
                  transform=ax_cards.transAxes)
    ax_cards.text(x + 0.095, 0.22, label, ha="center", va="center",
                  fontsize=10, color="white", transform=ax_cards.transAxes)

# Leaderboard
ax1 = fig.add_axes([0.05, 0.08, 0.42, 0.62])
lb = pd.read_csv(SQL / "09_pip_candidates__q1.csv").sort_values("composite_score")
pip_ids2 = pd.read_csv(SQL / "09_pip_candidates__q2.csv")["vendor_id"].tolist()
reward_ids2 = pd.read_csv(SQL / "09_pip_candidates__q3.csv")["vendor_id"].tolist()
colors2 = [NB_CORAL if vid in pip_ids2 else NB_TEAL if vid in reward_ids2 else NB_GREY
           for vid in lb["vendor_id"]]
ax1.barh(lb["vendor_name"], lb["composite_score"], color=colors2)
ax1.set_title("Vendor scoreboard")
ax1.set_xlim(60, 95); ax1.set_xlabel("Composite score")
ax1.tick_params(axis="y", labelsize=8)

# Monthly trend
ax2 = fig.add_axes([0.55, 0.42, 0.42, 0.28])
ax2.plot(overall["month"], overall["otd_pct"], marker="o", color=NB_INK, label="OTD %")
ax2b = ax2.twinx()
ax2b.plot(overall["month"],
          monthly.groupby("month")["defect_rate_pct"].mean().values,
          marker="s", color=NB_CORAL, label="Defect %")
ax2.set_title("Monthly OTD % and defect %"); ax2.set_ylabel("OTD %")
ax2b.set_ylabel("Defect %")

# Category heatmap
ax3 = fig.add_axes([0.55, 0.08, 0.42, 0.28])
im = ax3.imshow(mat, cmap="RdYlGn", aspect="auto",
                vmin=0, vmax=max(cat["otd_pct"].max(), 100))
ax3.set_yticks([0, 1]); ax3.set_yticklabels(["OTD %", "Defect %"])
ax3.set_xticks(range(len(cat))); ax3.set_xticklabels(cat["vendor_category"], rotation=15)
for i in range(2):
    for j in range(len(cat)):
        ax3.text(j, i, f"{mat[i, j]:.1f}", ha="center", va="center", fontsize=9)
ax3.set_title("Category performance")

fig.savefig(ROOT / "dashboard" / "mockups" / "page1_executive_summary.png",
            bbox_inches="tight", facecolor="white", dpi=110)
plt.close(fig)
print("  wrote dashboard/mockups/page1_executive_summary.png")

# --------------------------------------------------------------------------- #
# 12. Dashboard mockups — Vendor Deep-Dive (using PIP #1 as example)
# --------------------------------------------------------------------------- #
focus = pip_ids2[0] if pip_ids2 else "V005"
focus_row = lb_all[lb_all["vendor_id"] == focus].iloc[0]
focus_monthly = monthly[monthly["vendor_id"] == focus].sort_values("month")

fig = plt.figure(figsize=(14, 8))
fig.suptitle(f"Power BI — Page 2: Vendor Deep-Dive — {focus_row['vendor_name']} ({focus})",
             fontsize=15, fontweight="bold", y=0.995)

# Vendor KPI cards
ax_c = fig.add_axes([0.03, 0.78, 0.94, 0.16]); ax_c.axis("off")
vcards = [
    ("Total POs",      f"{int(focus_row['total_pos'])}",                NB_TEAL),
    ("OTD %",          f"{focus_row['otd_pct']:.1f}%",                  NB_INK),
    ("Defect rate",    f"{focus_row['defect_rate_pct']:.2f}%",          NB_CORAL),
    ("Fill rate",      f"{focus_row['fill_rate_pct']:.1f}%",            NB_SAND),
    ("Composite",      f"{focus_row['composite_score']:.1f}",           NB_TEAL),
]
for i, (label, val, col) in enumerate(vcards):
    x = 0.005 + i * 0.199
    ax_c.add_patch(plt.Rectangle((x, 0), 0.19, 1, facecolor=col, alpha=0.9,
                                 transform=ax_c.transAxes))
    ax_c.text(x + 0.095, 0.62, val, ha="center", va="center",
              fontsize=17, fontweight="bold", color="white", transform=ax_c.transAxes)
    ax_c.text(x + 0.095, 0.22, label, ha="center", va="center",
              fontsize=10, color="white", transform=ax_c.transAxes)

# Delivery buckets bar
focus_buck = buck[buck["vendor_id"] == focus].iloc[0]
ax4 = fig.add_axes([0.05, 0.42, 0.28, 0.28])
ax4.bar(["On time", "Slight", "Signif"],
        [focus_buck["on_time"], focus_buck["slightly_late"], focus_buck["significantly_late"]],
        color=[NB_TEAL, NB_SAND, NB_CORAL])
ax4.set_title("Delivery buckets")

# Quality trend
ax5 = fig.add_axes([0.38, 0.42, 0.28, 0.28])
ax5.plot(focus_monthly["month"], focus_monthly["defect_rate_pct"],
         marker="o", color=NB_CORAL)
ax5.set_title("Monthly defect rate %"); ax5.tick_params(axis="x", rotation=30)

# Price variance scatter (this vendor's POs)
merged_focus = merged[merged["vendor_id"] == focus]
ax6 = fig.add_axes([0.70, 0.42, 0.28, 0.28])
ax6.scatter(merged_focus["quantity_received"], merged_focus["variance_pct"],
            color=NB_INK, alpha=0.6)
ax6.axhline(0, color=NB_GREY, linestyle="--")
ax6.set_title("Price variance vs order size")
ax6.set_xlabel("Qty received"); ax6.set_ylabel("Variance %")

# Inspection coverage bar (this vendor vs peer avg)
ax7 = fig.add_axes([0.05, 0.08, 0.9, 0.25])
peer_cov = cov.sort_values("inspection_coverage_pct")
ax7.barh(peer_cov["vendor_name"], peer_cov["inspection_coverage_pct"],
         color=[NB_CORAL if v == focus else NB_GREY for v in peer_cov["vendor_id"]])
ax7.set_title(f"Inspection coverage vs peers ({focus} highlighted)")
ax7.set_xlabel("Coverage %")
ax7.tick_params(axis="y", labelsize=7)

fig.savefig(ROOT / "dashboard" / "mockups" / "page2_vendor_deep_dive.png",
            bbox_inches="tight", facecolor="white", dpi=110)
plt.close(fig)
print("  wrote dashboard/mockups/page2_vendor_deep_dive.png")

print("\nAll figures written to", FIG)

"""
Build the 6–8 page PDF report and 5-slide interview deck (PDF) using ReportLab.
Charts are embedded from /report/figures/.
"""
from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT   = Path(__file__).resolve().parent.parent
FIG    = ROOT / "report" / "figures"
SQL    = ROOT / "data" / "sql_outputs"
OUT_P  = ROOT / "report" / "vendor_performance_report.pdf"
OUT_D  = ROOT / "report" / "interview_deck.pdf"

# ---------- palette & styles -------------------------------------------------
NB_INK   = colors.HexColor("#1D3557")
NB_TEAL  = colors.HexColor("#0E7C86")
NB_CORAL = colors.HexColor("#E76F51")
NB_SAND  = colors.HexColor("#E9C46A")

ss = getSampleStyleSheet()

def _style(name, **kw):
    base = ss["BodyText"].clone(name)
    for k, v in kw.items():
        setattr(base, k, v)
    return base

H1    = _style("H1",    fontSize=20, leading=24, textColor=NB_INK,
               fontName="Helvetica-Bold", spaceAfter=12)
H2    = _style("H2",    fontSize=14, leading=18, textColor=NB_INK,
               fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6)
BODY  = _style("Body",  fontSize=10.5, leading=15, textColor=colors.black,
               spaceAfter=6)
BULL  = _style("Bull",  fontSize=10.5, leading=15, leftIndent=14,
               bulletIndent=2, spaceAfter=3)
NOTE  = _style("Note",  fontSize=9, leading=12, textColor=colors.grey,
               spaceAfter=6, fontName="Helvetica-Oblique")


def img(path, width_cm):
    p = FIG / path
    img_o = Image(str(p))
    scale = (width_cm * cm) / img_o.imageWidth
    img_o.drawWidth  = img_o.imageWidth  * scale
    img_o.drawHeight = img_o.imageHeight * scale
    return img_o


def kpi_table(df, cols, col_widths=None):
    data = [list(cols.values())]
    for _, row in df.iterrows():
        data.append([str(row[c]) for c in cols.keys()])
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NB_INK),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ALIGN",      (1, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.whitesmoke, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
    ]))
    return t


# ---------------------------------------------------------------------------
# LOAD ANALYSIS OUTPUTS
# ---------------------------------------------------------------------------
kpi_q1     = pd.read_csv(SQL / "01_basic_kpis__q1.csv").iloc[0]
kpi_q2     = pd.read_csv(SQL / "01_basic_kpis__q2.csv")
vendor_kpi = pd.read_csv(SQL / "02_vendor_level__q1.csv")
cat        = pd.read_csv(SQL / "04_category_analysis__q1.csv")
decline    = pd.read_csv(SQL / "06_quality_decline__q1.csv").head(5)
leader     = pd.read_csv(SQL / "09_pip_candidates__q1.csv")
pip        = pd.read_csv(SQL / "09_pip_candidates__q2.csv")
reward     = pd.read_csv(SQL / "09_pip_candidates__q3.csv")

# ===========================================================================
# 1) REPORT — 7 pages
# ===========================================================================
doc = SimpleDocTemplate(str(OUT_P), pagesize=A4,
                        leftMargin=1.8*cm, rightMargin=1.8*cm,
                        topMargin=1.6*cm, bottomMargin=1.6*cm,
                        title="NorthBridge Vendor Performance Report")
story = []

# --- Cover ----------------------------------------------------------------- #
story += [
    Paragraph("Vendor Performance Analytics", H1),
    Paragraph("NorthBridge Supplies Pvt. Ltd. — Jan–Sep 2025", H2),
    Spacer(1, 6),
    Paragraph(
        "This report supports quarterly vendor-review decisions. It identifies "
        "candidates for a Performance Improvement Plan (PIP) and vendors "
        "eligible for continued or expanded business, based on delivery, "
        "quality, and cost performance across ~1,400 purchase orders.",
        BODY),
    Spacer(1, 6),
    Paragraph(f"Prepared: {date.today():%d %b %Y} &nbsp;&nbsp;•&nbsp;&nbsp; "
              f"Author: Data Analytics (fresher project) &nbsp;•&nbsp; "
              f"Currency: INR", NOTE),
    Spacer(1, 12),
    img("06_vendor_leaderboard.png", 15),
    Spacer(1, 10),
    Paragraph("<b>Bottom line:</b> Three vendors are recommended for PIP review "
              f"— <font color='#E76F51'><b>"
              f"{', '.join(pip['vendor_name'].tolist())}</b></font>. "
              f"Three vendors are recommended for continued/expanded business "
              f"— <font color='#0E7C86'><b>"
              f"{', '.join(reward['vendor_name'].tolist())}</b></font>.", BODY),
    PageBreak(),
]

# --- Section 1 — Business problem ----------------------------------------- #
story += [
    Paragraph("1. Business problem", H2),
    Paragraph(
        "NorthBridge Supplies procures from 20 vendors across four categories "
        "(Packaging, Raw Materials, Logistics, MRO) and four regions (North, "
        "South, East, West India). Procurement leadership needs a quarterly, "
        "evidence-based view to answer:", BODY),
    Paragraph(
        "&#8226; Which three vendors should be placed on a Performance "
        "Improvement Plan (PIP) this quarter?", BULL),
    Paragraph(
        "&#8226; Which vendors should be considered for continued or increased "
        "business?", BULL),
    Paragraph(
        "The analysis <b>supports</b> the decision — it does not automatically "
        "recommend replacement. Sole-source vendors and total-cost-of-ownership "
        "considerations are outside the scope of this project.", BODY),

    Paragraph("2. Data & tools", H2),
    Paragraph(
        f"<b>Dataset:</b> {int(kpi_q1['total_pos']):,} purchase orders "
        f"({kpi_q1['earliest_order']} → {kpi_q1['latest_order']}), "
        f"{int(kpi_q1['unique_vendors'])} vendors, "
        f"{int(kpi_q1['unique_products'])} products, "
        f"total spend ₹{kpi_q1['total_spend_inr']/1e7:.2f} Cr. "
        "Quality inspections are performed on a subset of POs (~60% coverage), "
        "reflecting a realistic sampling-based QC process. "
        "Dataset is synthetic but deliberately dirty: duplicated POs, "
        "inconsistent vendor-name casing, ~1% missing delivery dates, "
        "~2% missing defect counts, and one seasonal dip.", BODY),
    Paragraph(
        "<b>Stack:</b> PostgreSQL 15 (16-compatible SQL), Python 3.11 "
        "(pandas, numpy, matplotlib, psycopg2, Faker), Power BI Desktop "
        "(dashboard mocked as static PNGs in this repo; DAX measures shipped "
        "as a separate file).", BODY),
    Spacer(1, 6),
    img("10_er_diagram.png", 15),
    PageBreak(),
]

# --- Section 3 — Methodology & KPIs --------------------------------------- #
story += [
    Paragraph("3. Methodology & KPI definitions", H2),
    Paragraph(
        "All KPIs are computed on cleaned tables (<i>*_clean</i>). The "
        "cleaning notebook logs every decision (duplicate PO drop, casing fix, "
        "zero-price flag, over-shipment flag, missing-defect handling).", BODY),
]
kpi_defs = [
    ["KPI", "Formula", "Scope / notes"],
    ["On-Time Delivery %",
     "count(actual ≤ promised) / count(delivered)",
     "Rows with missing actual date excluded from denominator"],
    ["Defect Rate %",
     "Σ defect_count / Σ inspected_qty × 100",
     "Inspected POs only. Missing defect filled 0 only when status=Passed"],
    ["Price Variance %",
     "(unit_price − agreed_price) / agreed_price × 100",
     "Rows with agreed_price=0 or NULL excluded"],
    ["Lead Time (days)",
     "actual_delivery_date − order_date",
     "Missing actual date excluded"],
    ["Fill Rate %",
     "quantity_received / quantity_ordered × 100 (capped at 100)",
     "Over-shipments flagged separately in data-quality view"],
    ["Composite Vendor Score",
     "0.40·OTD + 0.40·(100−Defect%) + 0.20·(100−max(0,PriceVar%))",
     "Eligibility ≥ 20 POs. Weights academic, not industry-standard"],
]
t = Table(kpi_defs, colWidths=[3.6*cm, 6.4*cm, 6.8*cm], hAlign="LEFT")
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NB_INK),
    ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
    ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE",   (0, 0), (-1, -1), 9),
    ("VALIGN",     (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
        [colors.whitesmoke, colors.white]),
    ("LEFTPADDING",  (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING",    (0, 0), (-1, -1), 4),
]))
story += [
    t, Spacer(1, 6),
    Paragraph(
        "<i>Disclaimer: The 40/40/20 composite weights were chosen for this "
        "academic project. They are not an industry-standard formula.</i>",
        NOTE),
    PageBreak(),
]

# --- Section 4 — Findings ------------------------------------------------- #
story += [
    Paragraph("4. Findings", H2),
    Paragraph("<b>4.1 Overall picture.</b> "
              f"Across {int(kpi_q1['total_pos']):,} POs, average vendor OTD "
              f"is {vendor_kpi['otd_pct'].mean():.1f}% and average defect "
              f"rate is {vendor_kpi['defect_rate_pct'].mean():.2f}%. "
              "Category-level performance shows Raw Materials with the "
              "weakest OTD, driven by longer promised lead times AND two "
              "chronically-late vendors.", BODY),
    img("07_category_heatmap.png", 14),

    Paragraph("<b>4.2 Delivery patterns.</b> "
              "The delay histogram is roughly centred around zero but with a "
              "long right tail — a handful of POs are severely late. When a "
              "vendor misses, they tend to miss badly.", BODY),
    img("04_delivery_delay_hist.png", 13),

    PageBreak(),

    Paragraph("<b>4.3 Quality trend — one vendor decline.</b> "
              "Comparing pre-M4 and post-M4 windows, "
              f"<b>{decline.iloc[0]['vendor_name']}</b>'s defect rate rose "
              f"from {decline.iloc[0]['pre_defect_pct']:.2f}% to "
              f"{decline.iloc[0]['post_defect_pct']:.2f}% "
              f"(Δ +{decline.iloc[0]['delta_pct']:.1f} pts). Other vendors "
              "move within noise ranges.", BODY),
    img("02_monthly_otd_trend.png", 14),

    Paragraph("Top 5 vendors by quality-decline delta:", BODY),
    kpi_table(decline,
              {"vendor_id": "Vendor",
               "vendor_name": "Name",
               "pre_n": "Pre-M4 inspections",
               "post_n": "Post-M4 inspections",
               "pre_defect_pct": "Pre %",
               "post_defect_pct": "Post %",
               "delta_pct": "Δ pts"},
              col_widths=[1.8*cm, 4.2*cm, 2.4*cm, 2.4*cm, 1.7*cm, 1.7*cm, 1.6*cm]),
    PageBreak(),
]

# --- Section 5 — PIP + Reward candidates ---------------------------------- #
story += [
    Paragraph("5. Recommended action list", H2),
    Paragraph("<b>5.1 PIP candidates (bottom-3 eligible with a delivery or "
              "quality issue).</b>", BODY),
    kpi_table(pip,
              {"vendor_id": "Vendor",
               "vendor_name": "Name",
               "total_pos": "POs",
               "otd_pct": "OTD %",
               "defect_rate_pct": "Defect %",
               "fill_rate_pct": "Fill %",
               "composite_score": "Score"},
              col_widths=[1.6*cm, 4.4*cm, 1.4*cm, 1.7*cm, 1.9*cm, 1.6*cm, 1.7*cm]),
]

for _, r in pip.iterrows():
    story.append(Paragraph(
        f"• <b>{r['vendor_name']}</b> ({r['vendor_id']}, "
        f"{r['vendor_category']}): OTD {r['otd_pct']:.1f}% "
        f"(benchmark {r['benchmark_otd']:.1f}%), "
        f"defect {r['defect_rate_pct']:.2f}% "
        f"(benchmark {r['benchmark_defect']:.2f}%), "
        f"composite {r['composite_score']:.1f}. "
        f"Selection driver: "
        f"{'OTD below benchmark' if r['otd_pct']<r['benchmark_otd'] else 'defect rate above benchmark'}"
        f"{' and defect rate above benchmark' if (r['otd_pct']<r['benchmark_otd'] and r['defect_rate_pct']>r['benchmark_defect']) else ''}.",
        BULL))

story += [
    Spacer(1, 6),
    Paragraph("<b>5.2 Reward candidates (top-3 eligible).</b>", BODY),
    kpi_table(reward,
              {"vendor_id": "Vendor",
               "vendor_name": "Name",
               "total_pos": "POs",
               "otd_pct": "OTD %",
               "defect_rate_pct": "Defect %",
               "fill_rate_pct": "Fill %",
               "composite_score": "Score"},
              col_widths=[1.6*cm, 4.4*cm, 1.4*cm, 1.7*cm, 1.9*cm, 1.6*cm, 1.7*cm]),
]

for _, r in reward.iterrows():
    story.append(Paragraph(
        f"• <b>{r['vendor_name']}</b> ({r['vendor_id']}, "
        f"{r['vendor_category']}): OTD {r['otd_pct']:.1f}%, "
        f"defect {r['defect_rate_pct']:.2f}%, fill {r['fill_rate_pct']:.1f}%, "
        f"composite {r['composite_score']:.1f}. "
        "Recommended for continued business; consider volume expansion "
        "subject to sole-source-risk check outside this analysis.", BULL))

story += [PageBreak()]

# --- Section 6 — Limitations & appendix ----------------------------------- #
story += [
    Paragraph("6. Limitations", H2),
    Paragraph("• No sole-source vendor logic — a low-scoring vendor may still "
              "be the only supplier for a critical SKU. Any PIP decision must "
              "be validated against category-manager input.", BULL),
    Paragraph("• Total-cost-of-ownership is not modelled. Price variance is "
              "an estimate; it ignores freight, quality-reject rework, and "
              "financing effects.", BULL),
    Paragraph("• Quality metrics reflect only inspected POs. Vendors with "
              "low inspection coverage (see chart below) have less reliable "
              "quality scores.", BULL),
    Paragraph("• The dataset is synthetic. Patterns are illustrative and "
              "not real market behaviour.", BULL),
    Paragraph("• Composite-score weights (40/40/20) are academic choices; "
              "an industry-standard scorecard would use category-specific "
              "weights, spend-weighting, and sensitivity analysis.", BULL),
    Paragraph("• Small-sample vendors (< 20 POs) are excluded from the "
              "leaderboard eligibility. This is why <i>Ashoka Papers</i> "
              "(17 POs) appears with a low score but is not shortlisted.", BULL),
    Spacer(1, 6),
    img("09_inspection_coverage.png", 15),

    Paragraph("7. Appendix — chart index", H2),
    Paragraph("Figures generated: order volume by vendor, monthly OTD trend, "
              "defect distribution, delivery delay histogram, price variance "
              "by category, vendor leaderboard, category heatmap, delivery "
              "buckets, inspection coverage, ER diagram, and two Power BI "
              "dashboard mockups (Executive Summary, Vendor Deep-Dive).", BODY),
]

doc.build(story)
print(f"wrote {OUT_P}")


# ===========================================================================
# 2) INTERVIEW DECK — 5 slides, landscape
# ===========================================================================
deck = SimpleDocTemplate(str(OUT_D), pagesize=landscape(A4),
                         leftMargin=1.5*cm, rightMargin=1.5*cm,
                         topMargin=1.2*cm, bottomMargin=1.2*cm,
                         title="Vendor Performance — Interview Deck")

SLIDE_H1 = _style("SlideH1", fontSize=26, leading=30, textColor=NB_INK,
                  fontName="Helvetica-Bold", spaceAfter=12)
SLIDE_H2 = _style("SlideH2", fontSize=16, leading=20, textColor=NB_TEAL,
                  fontName="Helvetica-Bold", spaceAfter=8)
SLIDE_BOD = _style("SlideBody", fontSize=13, leading=18, spaceAfter=6)
SLIDE_BUL = _style("SlideBull", fontSize=13, leading=18,
                   leftIndent=18, spaceAfter=4)

def slide_footer(n):
    return Paragraph(
        f"<font color='#B0B0B0'>{n}/5 &nbsp;•&nbsp; "
        f"Vendor Performance Analytics &nbsp;•&nbsp; NorthBridge Supplies</font>",
        _style("F", fontSize=9, leading=10))


slides = []

# Slide 1 — Business problem
slides += [
    Paragraph("1. Business Problem", SLIDE_H1),
    Paragraph("Which three vendors should we put on PIP this quarter — "
              "and which vendors deserve more business?", SLIDE_H2),
    Spacer(1, 6),
    Paragraph("&#8226; NorthBridge Supplies procures from 20 vendors "
              "across 4 categories and 4 regions.", SLIDE_BUL),
    Paragraph("&#8226; Procurement leadership needs an evidence-based "
              "quarterly review — not gut feel.", SLIDE_BUL),
    Paragraph("&#8226; Report <b>supports</b> the decision; sole-source "
              "and total-cost checks stay with the category manager.", SLIDE_BUL),
    Spacer(1, 20), slide_footer(1), PageBreak(),
]

# Slide 2 — Data & Tools
slides += [
    Paragraph("2. Data & Tools", SLIDE_H1),
    Paragraph(f"~1,400 POs • Jan–Sep 2025 • 20 vendors • ₹{kpi_q1['total_spend_inr']/1e7:.1f} Cr spend",
              SLIDE_H2),
    Paragraph("&#8226; 4-table star schema — vendors, products, "
              "purchase_orders (fact), quality_inspections (subset, ~60% "
              "coverage, UNIQUE po_number).", SLIDE_BUL),
    Paragraph("&#8226; Python (pandas + matplotlib) for cleaning & EDA — "
              "duplicates, casing, missing defects, over-shipments all "
              "handled with logged decisions.", SLIDE_BUL),
    Paragraph("&#8226; PostgreSQL 16 for KPI queries (CTEs, LEFT JOIN on "
              "inspections, window functions, LAG for MoM change).", SLIDE_BUL),
    Paragraph("&#8226; Power BI Desktop for the 2-page dashboard (mockups "
              "shipped as PNGs; DAX file included).", SLIDE_BUL),
    Spacer(1, 12), img("10_er_diagram.png", 22),
    slide_footer(2), PageBreak(),
]

# Slide 3 — Analysis & KPIs
slides += [
    Paragraph("3. Analysis & KPIs", SLIDE_H1),
    Paragraph("Five KPIs → one composite score, guarded by an "
              "eligibility rule", SLIDE_H2),
    Paragraph("&#8226; <b>OTD %</b>, <b>Defect Rate %</b> (inspected only), "
              "<b>Price Variance %</b>, <b>Lead Time</b>, <b>Fill Rate %</b>.",
              SLIDE_BUL),
    Paragraph("&#8226; <b>Composite = 0.4·OTD + 0.4·(100−Defect) + "
              "0.2·(100−max(0,PriceVar))</b>. Weights are academic — "
              "documented, not industry-standard.", SLIDE_BUL),
    Paragraph("&#8226; Vendors need ≥ 20 POs to be eligible → small-"
              "sample noise is filtered out (Ashoka Papers, 17 POs, is "
              "excluded even though its score is low).", SLIDE_BUL),
    Paragraph("&#8226; PIP filter: bottom-3 score AND below-avg OTD or "
              "above-avg defect rate. Prevents flagging a chronic-low-score "
              "vendor with no operational issue.", SLIDE_BUL),
    Spacer(1, 12), slide_footer(3), PageBreak(),
]

# Slide 4 — Dashboard & findings
slides += [
    Paragraph("4. Dashboard & Findings", SLIDE_H1),
    Paragraph("Executive Summary → Vendor Deep-Dive (drill-through)",
              SLIDE_H2),
    img("06_vendor_leaderboard.png", 17),
    Paragraph(f"&#8226; PIP shortlist: <font color='#E76F51'><b>"
              f"{', '.join(pip['vendor_name'].tolist())}</b></font>. "
              f"Reward shortlist: <font color='#0E7C86'><b>"
              f"{', '.join(reward['vendor_name'].tolist())}</b></font>.",
              SLIDE_BUL),
    Paragraph(f"&#8226; Sundar Logistics defect rate jumps "
              f"{decline.iloc[0]['pre_defect_pct']:.1f}% → "
              f"{decline.iloc[0]['post_defect_pct']:.1f}% after Month 4 — "
              "a directional issue an annual average would have hidden.",
              SLIDE_BUL),
    slide_footer(4), PageBreak(),
]

# Slide 5 — Recommendations & learnings
slides += [
    Paragraph("5. Recommendations & Learnings", SLIDE_H1),
    Paragraph("Business action → data & analytics learnings",
              SLIDE_H2),
    Paragraph("<b>Business:</b>", SLIDE_BOD),
    Paragraph(f"&#8226; Put <b>{', '.join(pip['vendor_name'].tolist())}</b> "
              "on a 90-day PIP; review after next quarter's data.", SLIDE_BUL),
    Paragraph(f"&#8226; Retain and consider expanding volumes with "
              f"<b>{', '.join(reward['vendor_name'].tolist())}</b> — pending "
              "sole-source and capacity checks with the category manager.",
              SLIDE_BUL),
    Paragraph("&#8226; Raise QC inspection coverage on vendors with low "
              "sample sizes before the next review.", SLIDE_BUL),
    Paragraph("<b>Learnings:</b>", SLIDE_BOD),
    Paragraph("&#8226; Averages can hide directional problems — always "
              "look at the trend.", SLIDE_BUL),
    Paragraph("&#8226; Explicit eligibility rules make a scoring "
              "system defensible.", SLIDE_BUL),
    Paragraph("&#8226; Documenting cleaning decisions is what separates "
              "an analyst from a spreadsheet.", SLIDE_BUL),
    slide_footer(5),
]

deck.build(slides)
print(f"wrote {OUT_D}")

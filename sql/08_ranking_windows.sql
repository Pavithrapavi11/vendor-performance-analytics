-- ============================================================================
-- 08_ranking_windows.sql
-- Question:  How does a vendor rank within its category, and how has its
--            monthly OTD moved (using LAG for quarter-over-quarter change)?
-- Why:       Demonstrates window functions (RANK, ROW_NUMBER, LAG) and
--            produces the leaderboard used on Dashboard Page 1.
-- Result:    (a) Ranked vendors within category by spend and by OTD.
--            (b) Monthly OTD delta per vendor.
-- Limitation: Ranks are only meaningful for vendors with enough POs.
-- ============================================================================

-- (a) Rankings within category ------------------------------------------------
WITH v_kpi AS (
    SELECT
        v.vendor_id, v.vendor_name, v.vendor_category,
        SUM(p.invoice_amount)                                                AS spend,
        100.0 * COUNT(*) FILTER (
            WHERE p.actual_delivery_date IS NOT NULL
              AND p.actual_delivery_date <= p.promised_date
        ) / NULLIF(COUNT(*) FILTER (WHERE p.actual_delivery_date IS NOT NULL), 0) AS otd_pct
    FROM vendors_clean v
    JOIN purchase_orders_clean p USING (vendor_id)
    GROUP BY v.vendor_id, v.vendor_name, v.vendor_category
)
SELECT
    vendor_id,
    vendor_name,
    vendor_category,
    ROUND(spend::numeric, 2)                                                 AS spend_inr,
    ROUND(otd_pct::numeric, 2)                                               AS otd_pct,
    RANK()       OVER (PARTITION BY vendor_category ORDER BY spend    DESC) AS rank_by_spend,
    ROW_NUMBER() OVER (PARTITION BY vendor_category ORDER BY otd_pct  DESC) AS rank_by_otd
FROM v_kpi
ORDER BY vendor_category, rank_by_spend;

-- (b) Monthly OTD change per vendor (LAG) ------------------------------------
WITH monthly AS (
    SELECT
        p.vendor_id,
        DATE_TRUNC('month', p.order_date)::date                              AS month,
        100.0 * COUNT(*) FILTER (
            WHERE p.actual_delivery_date IS NOT NULL
              AND p.actual_delivery_date <= p.promised_date
        ) / NULLIF(COUNT(*) FILTER (WHERE p.actual_delivery_date IS NOT NULL), 0) AS otd_pct
    FROM purchase_orders_clean p
    GROUP BY p.vendor_id, DATE_TRUNC('month', p.order_date)
)
SELECT
    vendor_id,
    month,
    ROUND(otd_pct::numeric, 2)                                               AS otd_pct,
    ROUND(LAG(otd_pct) OVER (PARTITION BY vendor_id ORDER BY month)::numeric, 2)
                                                                             AS prev_month_otd,
    ROUND((otd_pct - LAG(otd_pct) OVER (PARTITION BY vendor_id ORDER BY month))::numeric, 2)
                                                                             AS mom_delta
FROM monthly
ORDER BY vendor_id, month;

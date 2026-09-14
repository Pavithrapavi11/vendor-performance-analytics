-- ============================================================================
-- 04_category_analysis.sql
-- Question:  How does performance differ across the 4 vendor categories?
-- Why:       Category context prevents unfair comparisons (Logistics vendors
--            deliver in days; Raw Materials vendors in weeks).
-- Result:    One row per category with avg KPIs and total spend.
-- Limitation: Averaging across vendors of different sizes; not spend-weighted.
-- ============================================================================

WITH vendor_kpi AS (
    SELECT
        v.vendor_category,
        v.vendor_id,
        COUNT(*)                                                             AS pos,
        COUNT(*) FILTER (WHERE p.actual_delivery_date IS NOT NULL)           AS delivered,
        COUNT(*) FILTER (
            WHERE p.actual_delivery_date IS NOT NULL
              AND p.actual_delivery_date <= p.promised_date
        )                                                                    AS on_time,
        SUM(p.invoice_amount)                                                AS spend,
        AVG(100.0 * (p.unit_price - p.agreed_price) / p.agreed_price) FILTER (
            WHERE p.agreed_price > 0
        )                                                                    AS price_var,
        SUM(qi.defect_count)                                                 AS defects,
        SUM(qi.inspected_quantity)                                           AS insp_qty
    FROM purchase_orders_clean p
    JOIN vendors_clean v ON v.vendor_id = p.vendor_id
    LEFT JOIN quality_inspections_clean qi ON qi.po_number = p.po_number
    GROUP BY v.vendor_category, v.vendor_id
)
SELECT
    vendor_category,
    COUNT(DISTINCT vendor_id)                                                AS vendors,
    SUM(pos)                                                                 AS total_pos,
    ROUND(SUM(spend)::numeric, 2)                                            AS total_spend_inr,
    ROUND(100.0 * SUM(on_time) / NULLIF(SUM(delivered), 0), 2)               AS otd_pct,
    ROUND(100.0 * SUM(defects)::numeric / NULLIF(SUM(insp_qty), 0), 2)       AS defect_rate_pct,
    ROUND(AVG(price_var)::numeric, 2)                                        AS avg_price_var_pct
FROM vendor_kpi
GROUP BY vendor_category
ORDER BY otd_pct DESC;

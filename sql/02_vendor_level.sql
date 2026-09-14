-- ============================================================================
-- 02_vendor_level.sql
-- Question:  What are the five KPIs for each vendor?
-- Why:       Vendor-level KPIs feed everything else — the leaderboard, PIP
--            selection, dashboard scorecards. They must be defined once and
--            reused.
-- Result:    One row per vendor with OTD %, Defect Rate %, Price Variance %,
--            avg Lead Time, Fill Rate %, plus PO/inspection counts.
-- Limitation: Defect Rate is computed over INSPECTED POs only — a LEFT JOIN
--             is used so vendors with zero inspections still appear.
-- ============================================================================

WITH po_metrics AS (
    SELECT
        p.vendor_id,
        COUNT(*)                                                            AS total_pos,
        -- On-Time Delivery %: exclude rows with missing actual_delivery_date
        COUNT(*) FILTER (WHERE actual_delivery_date IS NOT NULL)            AS delivered_pos,
        COUNT(*) FILTER (
            WHERE actual_delivery_date IS NOT NULL
              AND actual_delivery_date <= promised_date
        )                                                                   AS on_time_pos,
        -- Lead time (days) on delivered POs only
        AVG(actual_delivery_date - order_date) FILTER (
            WHERE actual_delivery_date IS NOT NULL
        )                                                                   AS avg_lead_time_days,
        -- Fill Rate — capped at 100%; excludes cancelled rows to avoid noise
        AVG(LEAST(100.0, 100.0 * quantity_received::numeric / quantity_ordered)) FILTER (
            WHERE quantity_ordered > 0 AND order_status <> 'Cancelled'
        )                                                                   AS avg_fill_rate_pct,
        -- Price Variance % — excludes zero/null agreed_price
        AVG(100.0 * (unit_price - agreed_price) / agreed_price) FILTER (
            WHERE agreed_price IS NOT NULL AND agreed_price > 0
        )                                                                   AS avg_price_variance_pct,
        SUM(invoice_amount)                                                 AS total_spend_inr
    FROM purchase_orders_clean p
    GROUP BY p.vendor_id
),
qi_metrics AS (
    SELECT
        p.vendor_id,
        COUNT(qi.inspection_id)                                             AS inspected_pos,
        SUM(qi.inspected_quantity)                                          AS total_inspected_qty,
        SUM(qi.defect_count)                                                AS total_defects,
        CASE
            WHEN COALESCE(SUM(qi.inspected_quantity), 0) = 0 THEN NULL
            ELSE 100.0 * SUM(qi.defect_count)::numeric / SUM(qi.inspected_quantity)
        END                                                                 AS defect_rate_pct
    FROM purchase_orders_clean p
    LEFT JOIN quality_inspections_clean qi ON qi.po_number = p.po_number
    GROUP BY p.vendor_id
)
SELECT
    v.vendor_id,
    v.vendor_name,
    v.region,
    v.vendor_category,
    pm.total_pos,
    pm.total_spend_inr,
    ROUND(100.0 * pm.on_time_pos / NULLIF(pm.delivered_pos, 0), 2)          AS otd_pct,
    ROUND(pm.avg_lead_time_days::numeric, 2)                                AS avg_lead_time_days,
    ROUND(pm.avg_fill_rate_pct::numeric, 2)                                 AS avg_fill_rate_pct,
    ROUND(pm.avg_price_variance_pct::numeric, 2)                            AS avg_price_variance_pct,
    qm.inspected_pos,
    ROUND(100.0 * qm.inspected_pos / pm.total_pos, 2)                       AS inspection_coverage_pct,
    ROUND(qm.defect_rate_pct::numeric, 2)                                   AS defect_rate_pct
FROM vendors_clean v
JOIN po_metrics pm ON pm.vendor_id = v.vendor_id
LEFT JOIN qi_metrics qm ON qm.vendor_id = v.vendor_id
ORDER BY otd_pct DESC NULLS LAST;

-- ============================================================================
-- 03_monthly_trends.sql
-- Question:  How do vendor OTD % and Defect Rate % change month over month?
-- Why:       Trends surface problems that vendor-level averages hide (e.g. a
--            vendor whose quality collapses only in the last few months).
-- Result:    Vendor x month grid with OTD %, defect rate, PO count.
-- Limitation: Months with <3 POs for a vendor are unstable — the report
--             notes this rather than filtering them out.
-- ============================================================================

WITH monthly AS (
    SELECT
        p.vendor_id,
        DATE_TRUNC('month', p.order_date)::date                              AS month,
        COUNT(*)                                                             AS po_count,
        COUNT(*) FILTER (WHERE actual_delivery_date IS NOT NULL)             AS delivered,
        COUNT(*) FILTER (
            WHERE actual_delivery_date IS NOT NULL
              AND actual_delivery_date <= promised_date
        )                                                                    AS on_time,
        SUM(qi.inspected_quantity)                                           AS inspected_qty,
        SUM(qi.defect_count)                                                 AS defects
    FROM purchase_orders_clean p
    LEFT JOIN quality_inspections_clean qi ON qi.po_number = p.po_number
    GROUP BY p.vendor_id, DATE_TRUNC('month', p.order_date)
)
SELECT
    v.vendor_id,
    v.vendor_name,
    m.month,
    m.po_count,
    ROUND(100.0 * m.on_time / NULLIF(m.delivered, 0), 2)                     AS otd_pct,
    ROUND(100.0 * m.defects::numeric / NULLIF(m.inspected_qty, 0), 2)        AS defect_rate_pct
FROM monthly m
JOIN vendors_clean v USING (vendor_id)
ORDER BY v.vendor_id, m.month;

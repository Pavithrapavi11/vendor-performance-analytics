-- ============================================================================
-- 06_quality_decline.sql
-- Question:  Which vendors' defect rates worsened after Month 4 (May)?
-- Why:       Averages over 9 months mask directional problems. A vendor going
--            from 2% -> 12% defects needs different action than a steady 7%.
-- Result:    Vendors ranked by "post-M4 defect rate minus pre-M4 defect rate".
-- Limitation: Vendors with few inspections in either window will have noisy
--             deltas — the WHERE clause requires >=3 inspected POs per window.
-- ============================================================================

WITH inspected AS (
    SELECT
        p.vendor_id,
        EXTRACT(MONTH FROM p.order_date)::int AS mon,
        qi.inspected_quantity,
        qi.defect_count
    FROM purchase_orders_clean p
    JOIN quality_inspections_clean qi ON qi.po_number = p.po_number
),
windowed AS (
    SELECT
        vendor_id,
        SUM(CASE WHEN mon <= 4 THEN inspected_quantity END)  AS pre_qty,
        SUM(CASE WHEN mon <= 4 THEN defect_count       END)  AS pre_def,
        COUNT(*) FILTER (WHERE mon <= 4)                     AS pre_n,
        SUM(CASE WHEN mon >  4 THEN inspected_quantity END)  AS post_qty,
        SUM(CASE WHEN mon >  4 THEN defect_count       END)  AS post_def,
        COUNT(*) FILTER (WHERE mon >  4)                     AS post_n
    FROM inspected
    GROUP BY vendor_id
)
SELECT
    v.vendor_id,
    v.vendor_name,
    w.pre_n,
    w.post_n,
    ROUND(100.0 * w.pre_def  / NULLIF(w.pre_qty,  0), 2)                     AS pre_defect_pct,
    ROUND(100.0 * w.post_def / NULLIF(w.post_qty, 0), 2)                     AS post_defect_pct,
    ROUND(100.0 * w.post_def / NULLIF(w.post_qty, 0)
        - 100.0 * w.pre_def  / NULLIF(w.pre_qty,  0), 2)                     AS delta_pct
FROM windowed w
JOIN vendors_clean v USING (vendor_id)
WHERE w.pre_n >= 3 AND w.post_n >= 3
ORDER BY delta_pct DESC NULLS LAST;

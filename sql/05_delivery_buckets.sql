-- ============================================================================
-- 05_delivery_buckets.sql
-- Question:  When a vendor is late, HOW late are they?
-- Why:       An 80% OTD hides very different realities: 20% slightly late is
--            manageable; 20% significantly late is a production risk.
-- Result:    Vendor x bucket (On Time, Slightly Late 1–3d, Significantly Late >3d)
-- Limitation: Missing actual_delivery_date rows are excluded from the buckets.
-- ============================================================================

WITH bucketed AS (
    SELECT
        p.vendor_id,
        CASE
            WHEN p.actual_delivery_date IS NULL                              THEN 'Unknown'
            WHEN p.actual_delivery_date <= p.promised_date                   THEN 'On Time'
            WHEN p.actual_delivery_date - p.promised_date BETWEEN 1 AND 3    THEN 'Slightly Late'
            ELSE                                                                  'Significantly Late'
        END                                                                  AS delivery_bucket
    FROM purchase_orders_clean p
)
SELECT
    v.vendor_id,
    v.vendor_name,
    COUNT(*) FILTER (WHERE delivery_bucket = 'On Time')             AS on_time,
    COUNT(*) FILTER (WHERE delivery_bucket = 'Slightly Late')       AS slightly_late,
    COUNT(*) FILTER (WHERE delivery_bucket = 'Significantly Late')  AS significantly_late,
    COUNT(*) FILTER (WHERE delivery_bucket = 'Unknown')             AS unknown,
    COUNT(*)                                                        AS total_pos,
    ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_bucket = 'On Time')
          / COUNT(*) FILTER (WHERE delivery_bucket <> 'Unknown'), 2) AS otd_pct
FROM bucketed b
JOIN vendors_clean v USING (vendor_id)
GROUP BY v.vendor_id, v.vendor_name
ORDER BY otd_pct DESC;

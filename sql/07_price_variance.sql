-- ============================================================================
-- 07_price_variance.sql
-- Question:  Which vendors are systematically charging above the agreed price?
-- Why:       A 2% overcharge across a heavy vendor > a 20% overcharge on a
--            trivial one. Combine %variance with spend to prioritise.
-- Result:    Vendor-level avg price variance % + INR impact.
-- Limitation: Only compares to agreed_price; ignores total-cost-of-ownership
--             (freight, quality rejects). Report calls this out.
-- ============================================================================

WITH v_price AS (
    SELECT
        p.vendor_id,
        AVG(100.0 * (p.unit_price - p.agreed_price) / p.agreed_price) FILTER (
            WHERE p.agreed_price > 0
        )                                                                    AS avg_var_pct,
        SUM((p.unit_price - p.agreed_price) * p.quantity_received) FILTER (
            WHERE p.agreed_price > 0
        )                                                                    AS variance_inr,
        SUM(p.invoice_amount)                                                AS total_spend
    FROM purchase_orders_clean p
    GROUP BY p.vendor_id
)
SELECT
    v.vendor_id,
    v.vendor_name,
    v.vendor_category,
    ROUND(vp.total_spend::numeric, 2)                                        AS total_spend_inr,
    ROUND(vp.avg_var_pct::numeric, 2)                                        AS avg_price_variance_pct,
    ROUND(vp.variance_inr::numeric, 2)                                       AS price_impact_inr
FROM v_price vp
JOIN vendors_clean v USING (vendor_id)
ORDER BY avg_price_variance_pct DESC NULLS LAST;

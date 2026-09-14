-- ============================================================================
-- 09_pip_candidates.sql
-- Question:  Which vendors are candidates for a Performance Improvement Plan
--            this quarter, and which vendors should be rewarded?
-- Why:       This is the business ask. The composite score ranks vendors, and
--            the eligibility + issue rules make the PIP shortlist defensible.
-- Result:    (a) All eligible vendors with composite score.
--            (b) Top 3 PIP candidates (lowest composite score AND either
--                below-avg OTD or above-avg defect rate).
--            (c) Top 3 reward candidates (highest composite score).
-- Limitation: Weights (40/40/20) are academic; not industry standard. Vendors
--             with low inspection coverage have less reliable quality scores.
-- ============================================================================

-- ------------------------------------------------------------------
-- Base: per-vendor KPIs (mirrors 02_vendor_level.sql)
-- ------------------------------------------------------------------
DROP VIEW IF EXISTS v_vendor_kpi CASCADE;
CREATE VIEW v_vendor_kpi AS
WITH po_m AS (
    SELECT
        vendor_id,
        COUNT(*)                                                             AS total_pos,
        COUNT(*) FILTER (WHERE actual_delivery_date IS NOT NULL)             AS delivered,
        COUNT(*) FILTER (
            WHERE actual_delivery_date IS NOT NULL
              AND actual_delivery_date <= promised_date
        )                                                                    AS on_time,
        AVG(LEAST(100.0, 100.0 * quantity_received::numeric / quantity_ordered)) FILTER (
            WHERE quantity_ordered > 0 AND order_status <> 'Cancelled'
        )                                                                    AS fill_rate_pct,
        AVG(100.0 * (unit_price - agreed_price) / agreed_price) FILTER (
            WHERE agreed_price > 0
        )                                                                    AS price_var_pct
    FROM purchase_orders_clean
    GROUP BY vendor_id
),
qi_m AS (
    SELECT
        p.vendor_id,
        COUNT(qi.inspection_id)                                              AS inspected_pos,
        100.0 * SUM(qi.defect_count)::numeric / NULLIF(SUM(qi.inspected_quantity), 0)
                                                                             AS defect_rate_pct
    FROM purchase_orders_clean p
    LEFT JOIN quality_inspections_clean qi ON qi.po_number = p.po_number
    GROUP BY p.vendor_id
)
SELECT
    v.vendor_id,
    v.vendor_name,
    v.region,
    v.vendor_category,
    po_m.total_pos,
    ROUND((100.0 * po_m.on_time / NULLIF(po_m.delivered, 0))::numeric, 2)    AS otd_pct,
    ROUND(po_m.fill_rate_pct::numeric, 2)                                    AS fill_rate_pct,
    ROUND(po_m.price_var_pct::numeric, 2)                                    AS price_var_pct,
    qi_m.inspected_pos,
    ROUND(qi_m.defect_rate_pct::numeric, 2)                                  AS defect_rate_pct,
    -- Composite Score: 40% OTD + 40% Quality + 20% Cost
    ROUND((
        0.40 * COALESCE(100.0 * po_m.on_time / NULLIF(po_m.delivered, 0), 0)
      + 0.40 * (100.0 - COALESCE(qi_m.defect_rate_pct, 0))
      + 0.20 * (100.0 - GREATEST(0, COALESCE(po_m.price_var_pct, 0)))
    )::numeric, 2)                                                           AS composite_score
FROM vendors_clean v
JOIN po_m USING (vendor_id)
LEFT JOIN qi_m USING (vendor_id);

-- (a) Full leaderboard --------------------------------------------------------
SELECT * FROM v_vendor_kpi ORDER BY composite_score DESC;

-- ------------------------------------------------------------------
-- (b) PIP candidates (bottom 3 by score, with issue filter)
-- ------------------------------------------------------------------
WITH benchmarks AS (
    SELECT
        AVG(otd_pct)         AS avg_otd,
        AVG(defect_rate_pct) AS avg_defect
    FROM v_vendor_kpi
    WHERE total_pos >= 20
),
eligible AS (
    SELECT k.*, b.avg_otd, b.avg_defect
    FROM v_vendor_kpi k CROSS JOIN benchmarks b
    WHERE k.total_pos >= 20
),
qualifies AS (
    SELECT *,
           CASE WHEN otd_pct < avg_otd OR defect_rate_pct > avg_defect
                THEN TRUE ELSE FALSE END AS has_issue
    FROM eligible
),
pip AS (
    SELECT *
    FROM qualifies
    WHERE has_issue
    ORDER BY composite_score ASC
    LIMIT 3
)
SELECT
    'PIP' AS list,
    vendor_id, vendor_name, vendor_category, total_pos,
    otd_pct, defect_rate_pct, fill_rate_pct, price_var_pct, composite_score,
    ROUND(avg_otd::numeric,    2)  AS benchmark_otd,
    ROUND(avg_defect::numeric, 2)  AS benchmark_defect
FROM pip
ORDER BY composite_score ASC;

-- ------------------------------------------------------------------
-- (c) Reward candidates (top 3 by score)
-- ------------------------------------------------------------------
SELECT
    'REWARD' AS list,
    vendor_id, vendor_name, vendor_category, total_pos,
    otd_pct, defect_rate_pct, fill_rate_pct, price_var_pct, composite_score
FROM v_vendor_kpi
WHERE total_pos >= 20
ORDER BY composite_score DESC
LIMIT 3;

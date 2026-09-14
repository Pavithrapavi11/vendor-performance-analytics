-- ============================================================================
-- 01_basic_kpis.sql
-- Question:  What is the overall shape of procurement spend and volume?
-- Why:       Interviewer's first question is always "how big is the dataset".
--            Answering with totals and averages sets the stage.
-- Result:    Single-row snapshot of total POs, unique vendors, spend, avg values.
-- Limitation: Uses raw purchase_orders_clean. Does not weight by category.
-- ============================================================================

SELECT
    COUNT(*)                                       AS total_pos,
    COUNT(DISTINCT vendor_id)                      AS unique_vendors,
    COUNT(DISTINCT product_id)                     AS unique_products,
    ROUND(SUM(invoice_amount)::numeric, 2)         AS total_spend_inr,
    ROUND(AVG(invoice_amount)::numeric, 2)         AS avg_po_value_inr,
    MIN(order_date)                                AS earliest_order,
    MAX(order_date)                                AS latest_order
FROM purchase_orders_clean;

-- Spend by order status (sanity check — Cancelled should be a tiny share)
SELECT
    order_status,
    COUNT(*)                                       AS po_count,
    ROUND(SUM(invoice_amount)::numeric, 2)         AS spend_inr,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_pos
FROM purchase_orders_clean
GROUP BY order_status
ORDER BY po_count DESC;

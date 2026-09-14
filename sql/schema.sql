-- ============================================================================
-- NorthBridge Supplies Pvt. Ltd. — Vendor Performance Analytics
-- Schema: 4 tables (PostgreSQL 15/16 compatible)
-- ============================================================================
-- Design notes:
--   * purchase_orders is the FACT table (grain: one row per PO line).
--   * vendors and products are DIMENSION tables.
--   * quality_inspections holds AT MOST one record per PO — enforced by the
--     UNIQUE constraint on po_number. Only a subset of POs (~55–65%) are
--     inspected, reflecting a realistic sampling-based QC process.
--   * All monetary values are in INR. Dates are DATE (no timezone).
-- ============================================================================

DROP TABLE IF EXISTS quality_inspections CASCADE;
DROP TABLE IF EXISTS purchase_orders   CASCADE;
DROP TABLE IF EXISTS products          CASCADE;
DROP TABLE IF EXISTS vendors           CASCADE;

-- ---------------------------------------------------------------------------
-- Dimension: vendors
-- ---------------------------------------------------------------------------
CREATE TABLE vendors (
    vendor_id           VARCHAR(10)  PRIMARY KEY,
    vendor_name         VARCHAR(120) NOT NULL,
    region              VARCHAR(20)  NOT NULL,           -- North / South / East / West
    vendor_category     VARCHAR(40)  NOT NULL,           -- Packaging / Raw Materials / Logistics / MRO
    contract_start_date DATE         NOT NULL,
    payment_terms       VARCHAR(20)  NOT NULL            -- e.g. Net 30 / Net 45 / Net 60
);

-- ---------------------------------------------------------------------------
-- Dimension: products
-- ---------------------------------------------------------------------------
CREATE TABLE products (
    product_id           VARCHAR(10)   PRIMARY KEY,
    product_name         VARCHAR(120)  NOT NULL,
    category             VARCHAR(40)   NOT NULL,
    standard_unit_price  NUMERIC(12,2) NOT NULL           -- INR
);

-- ---------------------------------------------------------------------------
-- Fact: purchase_orders
-- ---------------------------------------------------------------------------
CREATE TABLE purchase_orders (
    po_number             VARCHAR(20)   PRIMARY KEY,
    vendor_id             VARCHAR(10)   NOT NULL REFERENCES vendors(vendor_id),
    product_id            VARCHAR(10)   NOT NULL REFERENCES products(product_id),
    order_date            DATE          NOT NULL,
    promised_date         DATE          NOT NULL,
    actual_delivery_date  DATE,                            -- NULL allowed (in-transit / missing)
    quantity_ordered      INTEGER       NOT NULL,
    quantity_received     INTEGER,
    unit_price            NUMERIC(12,2) NOT NULL,          -- price actually paid
    agreed_price          NUMERIC(12,2),                   -- contractual price (can be NULL / 0 for dirty rows)
    invoice_amount        NUMERIC(14,2),
    order_status          VARCHAR(20)   NOT NULL           -- Delivered / Partial / In-Transit / Cancelled
);

CREATE INDEX idx_po_vendor  ON purchase_orders(vendor_id);
CREATE INDEX idx_po_product ON purchase_orders(product_id);
CREATE INDEX idx_po_order_date ON purchase_orders(order_date);

-- ---------------------------------------------------------------------------
-- Fact-adjacent: quality_inspections
-- One inspection per inspected PO. UNIQUE guarantees the 1:1 relationship.
-- ---------------------------------------------------------------------------
CREATE TABLE quality_inspections (
    inspection_id      VARCHAR(15)  PRIMARY KEY,
    po_number          VARCHAR(20)  NOT NULL UNIQUE REFERENCES purchase_orders(po_number),
    inspection_date    DATE         NOT NULL,
    inspected_quantity INTEGER      NOT NULL,
    defect_count       INTEGER,                    -- NULL for ~2% of rows (intentional dirt)
    complaint_count    INTEGER      NOT NULL DEFAULT 0,
    quality_status     VARCHAR(20)  NOT NULL       -- Passed / Failed / Conditional
);

CREATE INDEX idx_qi_po ON quality_inspections(po_number);

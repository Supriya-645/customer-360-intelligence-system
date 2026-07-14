-- Add primary keys and indexes now that bulk load is complete.
-- Doing this AFTER loading avoids the overhead of constraint checks on every row during a large insert.

-- Primary keys: enforce uniqueness where each row genuinely represents one entity
ALTER TABLE raw_application_train ADD CONSTRAINT pk_application_train PRIMARY KEY (sk_id_curr);
ALTER TABLE raw_bureau ADD CONSTRAINT pk_bureau PRIMARY KEY (sk_id_bureau);

-- Indexes on SK_ID_CURR: every feature-engineering query in Phase 6 will GROUP BY or JOIN
-- on this column across millions of rows, so an index here is essential for reasonable query speed.
CREATE INDEX idx_installments_sk_id_curr ON raw_installments_payments (sk_id_curr);
CREATE INDEX idx_credit_card_sk_id_curr ON raw_credit_card_balance (sk_id_curr);
CREATE INDEX idx_pos_cash_sk_id_curr ON raw_pos_cash_balance (sk_id_curr);
CREATE INDEX idx_bureau_sk_id_curr ON raw_bureau (sk_id_curr);

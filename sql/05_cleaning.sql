-- Confirm the DAYS_EMPLOYED anomaly and see how many rows are affected
SELECT
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE days_employed = 365243) AS anomalous_rows,
    ROUND(100.0 * COUNT(*) FILTER (WHERE days_employed = 365243) / COUNT(*), 2) AS pct_anomalous
FROM raw_application_train;

-- Check the CODE_GENDER 'XNA' placeholder we excluded earlier
SELECT code_gender, COUNT(*)
FROM raw_application_train
GROUP BY code_gender;

-- Check for extreme outliers in income — a classic issue in this dataset
SELECT
    MIN(amt_income_total) AS min_income,
    MAX(amt_income_total) AS max_income,
    ROUND(AVG(amt_income_total), 0) AS avg_income,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amt_income_total) AS median_income,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY amt_income_total) AS p99_income
FROM raw_application_train;

-- How many rows sit above a sane income ceiling?
SELECT COUNT(*)
FROM raw_application_train
WHERE amt_income_total > 20000000;

-- Cleaned view of application_train: fixes structural data issues,
-- leaves statistical work (imputation, scaling) for Python in Phase 8.
CREATE OR REPLACE VIEW stg_application_train AS
SELECT
    *,
    CASE WHEN days_employed = 365243 THEN NULL ELSE days_employed END AS days_employed_clean,
    LEAST(amt_income_total, 20000000) AS amt_income_total_clean
FROM raw_application_train
WHERE code_gender != 'XNA';

SELECT COUNT(*), MAX(amt_income_total_clean), COUNT(*) - COUNT(days_employed_clean) AS still_have_nulls
FROM stg_application_train;

SELECT COUNT(*), COUNT(*) - COUNT(amt_payment) AS null_payments
FROM raw_installments_payments;

SELECT COUNT(*) FILTER (WHERE amt_credit_limit_actual = 0) AS zero_limit_rows
FROM raw_credit_card_balance;

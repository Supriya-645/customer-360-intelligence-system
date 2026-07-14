-- How many customers, and what fraction defaulted?
SELECT
    COUNT(*) AS total_customers,
    SUM(target) AS total_defaults,
    ROUND(100.0 * SUM(target) / COUNT(*), 2) AS default_rate_pct
FROM raw_application_train;

-- Missing values on the columns most likely to matter for risk scoring
SELECT
    COUNT(*) AS total_rows,
    COUNT(*) - COUNT(ext_source_1) AS missing_ext_source_1,
    COUNT(*) - COUNT(ext_source_2) AS missing_ext_source_2,
    COUNT(*) - COUNT(ext_source_3) AS missing_ext_source_3,
    COUNT(*) - COUNT(amt_annuity) AS missing_amt_annuity,
    COUNT(*) - COUNT(amt_goods_price) AS missing_amt_goods_price,
    COUNT(*) - COUNT(occupation_type) AS missing_occupation_type
FROM raw_application_train;

-- Does any SK_ID_CURR appear more than once? (it shouldn't, given our primary key — this doubles as a PK sanity check)
SELECT sk_id_curr, COUNT(*) AS row_count
FROM raw_application_train
GROUP BY sk_id_curr
HAVING COUNT(*) > 1;

-- Loan type distribution, and how big are these loans on average?
SELECT
    name_contract_type,
    COUNT(*) AS num_customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_portfolio,
    ROUND(AVG(amt_credit), 0) AS avg_loan_amount,
    ROUND(AVG(amt_income_total), 0) AS avg_income
FROM raw_application_train
GROUP BY name_contract_type
ORDER BY num_customers DESC;

-- Age and gender breakdown, with default rate per segment
SELECT
    code_gender,
    CASE
        WHEN -days_birth / 365 < 30 THEN 'Under 30'
        WHEN -days_birth / 365 < 45 THEN '30-44'
        WHEN -days_birth / 365 < 60 THEN '45-59'
        ELSE '60+'
    END AS age_bucket,
    COUNT(*) AS num_customers,
    ROUND(100.0 * SUM(target) / COUNT(*), 2) AS default_rate_pct
FROM raw_application_train
WHERE code_gender != 'XNA'
GROUP BY code_gender, age_bucket
ORDER BY code_gender, age_bucket;

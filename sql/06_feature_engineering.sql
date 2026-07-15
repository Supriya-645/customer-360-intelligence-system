-- Payment behavior: lateness aggregates per customer
WITH payment_lateness AS (
    SELECT
        sk_id_curr,
        days_entry_payment - days_instalment AS days_late
    FROM raw_installments_payments
    WHERE days_entry_payment IS NOT NULL  -- exclude the 2,905 unpaid-so-far installments for now; handled separately below
)
SELECT
    sk_id_curr,
    COUNT(*) AS total_installments,
    COUNT(*) FILTER (WHERE days_late > 0) AS num_late_payments,
    ROUND(AVG(days_late) FILTER (WHERE days_late > 0), 1) AS avg_days_late,
    MAX(days_late) AS max_days_late
FROM payment_lateness
GROUP BY sk_id_curr
LIMIT 20;

-- Distribution of lateness among late payments only
SELECT
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_late) AS median_late,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY days_late) AS p95_late,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY days_late) AS p99_late,
    MAX(days_late) AS max_late
FROM (
    SELECT days_entry_payment - days_instalment AS days_late
    FROM raw_installments_payments
    WHERE days_entry_payment IS NOT NULL
) t
WHERE days_late > 0;

-- Missed payments: installments that were due but genuinely never recorded as paid
SELECT
    sk_id_curr,
    COUNT(*) AS num_missed_payments
FROM raw_installments_payments
WHERE days_entry_payment IS NULL
GROUP BY sk_id_curr
LIMIT 20;

-- Is this customer's lateness getting worse or better over the life of their loans?
WITH payment_lateness AS (
    SELECT
        sk_id_curr,
        days_entry_payment - days_instalment AS days_late,
        ROW_NUMBER() OVER (PARTITION BY sk_id_curr ORDER BY days_instalment DESC) AS recency_rank,
        COUNT(*) OVER (PARTITION BY sk_id_curr) AS total_installments
    FROM raw_installments_payments
    WHERE days_entry_payment IS NOT NULL
)
SELECT
    sk_id_curr,
    ROUND(AVG(days_late) FILTER (WHERE recency_rank <= total_installments / 2), 1) AS avg_late_recent_half,
    ROUND(AVG(days_late) FILTER (WHERE recency_rank > total_installments / 2), 1) AS avg_late_earlier_half,
    ROUND(
        AVG(days_late) FILTER (WHERE recency_rank <= total_installments / 2)
        - AVG(days_late) FILTER (WHERE recency_rank > total_installments / 2), 1
    ) AS lateness_trend
FROM payment_lateness
GROUP BY sk_id_curr
LIMIT 20;

-- Credit utilization: overall level and recent-vs-prior trend
WITH monthly_utilization AS (
    SELECT
        sk_id_curr,
        months_balance,
        amt_balance / NULLIF(amt_credit_limit_actual, 0) AS utilization
    FROM raw_credit_card_balance
)
SELECT
    sk_id_curr,
    ROUND(AVG(utilization), 3) AS avg_utilization_overall,
    ROUND(AVG(utilization) FILTER (WHERE months_balance >= -6), 3) AS avg_utilization_recent_6mo,
    ROUND(AVG(utilization) FILTER (WHERE months_balance BETWEEN -12 AND -7), 3) AS avg_utilization_prior_6mo,
    ROUND(
        AVG(utilization) FILTER (WHERE months_balance >= -6)
        - AVG(utilization) FILTER (WHERE months_balance BETWEEN -12 AND -7), 3
    ) AS utilization_trend
FROM monthly_utilization
GROUP BY sk_id_curr
LIMIT 20;

-- DPD trend on POS/cash loans: is days-past-due getting worse or better recently?
SELECT
    sk_id_curr,
    ROUND(AVG(sk_dpd), 1) AS avg_dpd_overall,
    MAX(sk_dpd) AS max_dpd_ever,
    ROUND(AVG(sk_dpd) FILTER (WHERE months_balance >= -6), 1) AS avg_dpd_recent_6mo,
    ROUND(AVG(sk_dpd) FILTER (WHERE months_balance BETWEEN -12 AND -7), 1) AS avg_dpd_prior_6mo,
    ROUND(
        AVG(sk_dpd) FILTER (WHERE months_balance >= -6)
        - AVG(sk_dpd) FILTER (WHERE months_balance BETWEEN -12 AND -7), 1
    ) AS dpd_trend
FROM raw_pos_cash_balance
GROUP BY sk_id_curr
LIMIT 20;

-- External credit history: how much does this customer owe elsewhere, and for how long have they had credit at all?
SELECT
    sk_id_curr,
    COUNT(*) AS num_bureau_accounts,
    COUNT(*) FILTER (WHERE credit_active = 'Active') AS num_active_accounts,
    COUNT(*) FILTER (WHERE credit_active = 'Closed') AS num_closed_accounts,
    -MIN(days_credit) AS credit_history_length_days,
    MAX(credit_day_overdue) AS max_external_overdue_days,
    ROUND(SUM(amt_credit_sum_debt), 0) AS total_external_debt
FROM raw_bureau
GROUP BY sk_id_curr
LIMIT 20;

-- Final assembly: one row per customer, combining demographics + all 4 behavioral feature sets
DROP TABLE IF EXISTS customer_features;
CREATE TABLE customer_features AS
WITH payment_calc AS (
    SELECT
        sk_id_curr,
        days_entry_payment - days_instalment AS days_late,
        days_entry_payment,
        ROW_NUMBER() OVER (PARTITION BY sk_id_curr ORDER BY days_instalment DESC) AS recency_rank,
        COUNT(*) OVER (PARTITION BY sk_id_curr) AS total_installments
    FROM raw_installments_payments
),
payment_features AS (
    SELECT
        sk_id_curr,
        COUNT(*) AS total_installments,
        COUNT(*) FILTER (WHERE days_late > 0) AS num_late_payments,
        COUNT(*) FILTER (WHERE days_entry_payment IS NULL) AS num_missed_payments,
        ROUND(AVG(days_late) FILTER (WHERE days_late > 0), 1) AS avg_days_late,
        MAX(days_late) AS max_days_late,
        ROUND(
            AVG(days_late) FILTER (WHERE recency_rank <= total_installments / 2 AND days_late IS NOT NULL)
            - AVG(days_late) FILTER (WHERE recency_rank > total_installments / 2 AND days_late IS NOT NULL), 1
        ) AS lateness_trend
    FROM payment_calc
    GROUP BY sk_id_curr
),
credit_card_features AS (
    SELECT
        sk_id_curr,
        ROUND(AVG(amt_balance / NULLIF(amt_credit_limit_actual, 0)), 3) AS avg_utilization_overall,
        ROUND(
            AVG(amt_balance / NULLIF(amt_credit_limit_actual, 0)) FILTER (WHERE months_balance >= -6)
            - AVG(amt_balance / NULLIF(amt_credit_limit_actual, 0)) FILTER (WHERE months_balance BETWEEN -12 AND -7), 3
        ) AS utilization_trend
    FROM raw_credit_card_balance
    GROUP BY sk_id_curr
),
pos_cash_features AS (
    SELECT
        sk_id_curr,
        ROUND(AVG(sk_dpd), 1) AS avg_dpd_overall,
        MAX(sk_dpd) AS max_dpd_ever,
        ROUND(
            AVG(sk_dpd) FILTER (WHERE months_balance >= -6)
            - AVG(sk_dpd) FILTER (WHERE months_balance BETWEEN -12 AND -7), 1
        ) AS dpd_trend
    FROM raw_pos_cash_balance
    GROUP BY sk_id_curr
),
bureau_features AS (
    SELECT
        sk_id_curr,
        COUNT(*) AS num_bureau_accounts,
        COUNT(*) FILTER (WHERE credit_active = 'Active') AS num_active_accounts,
        COUNT(*) FILTER (WHERE credit_active = 'Closed') AS num_closed_accounts,
        -MIN(days_credit) AS credit_history_length_days,
        MAX(credit_day_overdue) AS max_external_overdue_days,
        ROUND(SUM(amt_credit_sum_debt), 0) AS total_external_debt
    FROM raw_bureau
    GROUP BY sk_id_curr
)
SELECT
    a.sk_id_curr,
    a.target,
    a.name_contract_type,
    a.code_gender,
    ROUND(-a.days_birth / 365.0, 1) AS age_years,
    ROUND(-a.days_employed_clean / 365.0, 1) AS employment_years,
    a.amt_income_total_clean AS income,
    a.amt_credit,
    a.amt_annuity,
    a.cnt_children,
    a.cnt_fam_members,
    a.name_education_type,
    a.name_family_status,
    a.name_housing_type,
    a.occupation_type,
    a.ext_source_1,
    a.ext_source_2,
    a.ext_source_3,
    p.total_installments,
    p.num_late_payments,
    p.num_missed_payments,
    p.avg_days_late,
    p.max_days_late,
    p.lateness_trend,
    c.avg_utilization_overall,
    c.utilization_trend,
    pc.avg_dpd_overall,
    pc.max_dpd_ever,
    pc.dpd_trend,
    b.num_bureau_accounts,
    b.num_active_accounts,
    b.num_closed_accounts,
    b.credit_history_length_days,
    b.max_external_overdue_days,
    b.total_external_debt
FROM stg_application_train a
LEFT JOIN payment_features p ON a.sk_id_curr = p.sk_id_curr
LEFT JOIN credit_card_features c ON a.sk_id_curr = c.sk_id_curr
LEFT JOIN pos_cash_features pc ON a.sk_id_curr = pc.sk_id_curr
LEFT JOIN bureau_features b ON a.sk_id_curr = b.sk_id_curr;

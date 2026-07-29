-- Combined view for Power BI: one clean object joining customer_features (demographics +
-- behavioral signals) with customer_scores (Risk/Collection/Cross-Sell/Health), so Power BI
-- connects to a single source instead of juggling two tables and manual DAX joins.

DROP VIEW IF EXISTS vw_customer_dashboard;
CREATE VIEW vw_customer_dashboard AS
SELECT
    f.sk_id_curr,
    f.target,
    f.name_contract_type,
    f.code_gender,
    f.age_years,
    f.employment_years,
    f.income,
    f.amt_credit,
    f.amt_annuity,
    f.name_education_type,
    f.name_family_status,
    f.name_housing_type,
    f.occupation_type,
    f.num_late_payments,
    f.avg_days_late,
    f.lateness_trend,
    f.avg_utilization_overall,
    f.utilization_trend,
    f.avg_dpd_overall,
    f.max_dpd_ever,
    f.dpd_trend,
    f.num_bureau_accounts,
    f.total_external_debt,
    s.risk_probability,
    s.risk_score,
    s.risk_segment,
    s.collection_priority_score,
    s.collection_rank,
    s.cross_sell_eligible,
    s.health_score,
    s.health_segment
FROM customer_features f
JOIN customer_scores s ON f.sk_id_curr = s.sk_id_curr;

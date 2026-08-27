"""
Behavioral Scorecard — new addition for Tessaract 2.0 alignment.

Distinct from the Risk Score on purpose: Risk Score comes from the trained model
(driven heavily by external bureau scores - ext_source_1/2/3). Behavioral Score
instead summarizes the customer's own observed payment discipline directly from
transaction-level history, independent of any external bureau input. It's a
genuinely different signal: two customers with an identical Risk Score can have
very different day-to-day payment behavior, and vice versa.

Built only from columns already present in customer_features (see
sql/06_feature_engineering.sql) - no fabricated inputs.

Formula (documented, not arbitrary):
    100
    - 40 x late_payment_rate          (fraction of installments paid late)
    - min(num_missed_payments x 5, 20)   (missed payments are worse than merely late ones, capped)
    - min(avg_dpd_overall, 20)            (days-past-due severity, capped)
    - 10 if any trend (lateness/dpd/utilization) is worsening, else 0
Clipped to [0, 100].

Weight rationale: late-payment *rate* (not raw count) is the primary driver (40 pts
max) since it's normalized and comparable across customers with different loan
counts. Missed payments and DPD are each capped at 20 points so no single extreme
value (e.g. one very high avg_dpd_overall) can single-handedly zero out the score -
consistent with the outlier-handling decisions made earlier in the project (Phase 6/7).
The trend penalty is a flat 10-point deduction, not scaled by trend magnitude, since
its role here is a binary "getting worse right now" flag, not a second measure of severity.
"""
from dataclasses import dataclass


@dataclass
class BehavioralResult:
    behavioral_score: float
    behavioral_band: str


def compute_behavioral_score(
    total_installments: int,
    num_late_payments: int,
    num_missed_payments: int,
    avg_dpd_overall: float,
    lateness_trend: float,
    dpd_trend: float,
    utilization_trend: float,
) -> float:
    total = total_installments or 0
    late_payment_rate = (num_late_payments / total) if total > 0 else 0.0

    missed_penalty = min((num_missed_payments or 0) * 5, 20)
    dpd_penalty = min(avg_dpd_overall or 0, 20)

    worsening = any(
        (t or 0) > 0 for t in (lateness_trend, dpd_trend, utilization_trend)
    )
    trend_penalty = 10 if worsening else 0

    score = 100 - (40 * late_payment_rate) - missed_penalty - dpd_penalty - trend_penalty
    return round(max(0.0, min(100.0, score)), 1)


def behavioral_band(score: float) -> str:
    if score >= 75:
        return "Strong"
    elif score >= 50:
        return "Fair"
    return "Weak"


def score_customer(
    total_installments: int,
    num_late_payments: int,
    num_missed_payments: int,
    avg_dpd_overall: float,
    lateness_trend: float,
    dpd_trend: float,
    utilization_trend: float,
) -> BehavioralResult:
    score = compute_behavioral_score(
        total_installments, num_late_payments, num_missed_payments,
        avg_dpd_overall, lateness_trend, dpd_trend, utilization_trend,
    )
    return BehavioralResult(behavioral_score=score, behavioral_band=behavioral_band(score))

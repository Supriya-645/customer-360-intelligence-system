"""
Cross-Sell / Propensity Scorecard — deliberately rule-based, not a model.

Real-world reasoning (also documented in the project README): businesses extending
*more* credit to a customer start with transparent, auditable rules before ever
trusting a black-box model to greenlight it. This mirrors that: eligibility is a
simple AND of three business-legible conditions.
"""
from dataclasses import dataclass

RISK_SCORE_MAX = 20
UTILIZATION_MAX = 0.40


@dataclass
class PropensityResult:
    eligible: bool
    cross_sell_opportunity: float  # 0 or 100, used inside the Health Score formula
    reason_codes: list


def evaluate_cross_sell(risk_score: float, num_late_payments: int, avg_utilization_overall: float) -> PropensityResult:
    utilization = avg_utilization_overall if avg_utilization_overall is not None else 0.0

    reasons = []
    if risk_score >= RISK_SCORE_MAX:
        reasons.append("RISK_SCORE_TOO_HIGH")
    if num_late_payments and num_late_payments > 0:
        reasons.append("HAS_LATE_PAYMENTS")
    if utilization >= UTILIZATION_MAX:
        reasons.append("UTILIZATION_TOO_HIGH")

    eligible = len(reasons) == 0
    if eligible:
        reasons = ["LOW_RISK", "NO_LATE_PAYMENTS", "HEALTHY_UTILIZATION"]

    return PropensityResult(
        eligible=eligible,
        cross_sell_opportunity=100.0 if eligible else 0.0,
        reason_codes=reasons,
    )

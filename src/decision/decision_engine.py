"""
Decision Engine — deterministic rules, not a model.

Critical architectural distinction: the ML model (src/models) and the scorecards
(src/scorecards) produce *scores*. This module converts scores into *business
actions*. Keeping this separation explicit matters for a financial-decisioning
system - a risk committee can audit, adjust, or override the decision rules
without retraining anything, and every decision traces back to explicit,
readable reason codes rather than a model's internal state.
"""
from dataclasses import dataclass, field


@dataclass
class Decision:
    risk_band: str
    collection_priority: str
    cross_sell_opportunity: str
    behavioral_band: str
    health_segment: str
    recommended_action: str
    reason_codes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "risk_band": self.risk_band,
            "collection_priority": self.collection_priority,
            "cross_sell_opportunity": self.cross_sell_opportunity,
            "behavioral_band": self.behavioral_band,
            "health_segment": self.health_segment,
            "recommended_action": self.recommended_action,
            "reason_codes": self.reason_codes,
        }


def _collection_priority_band(collection_priority_score: float) -> str:
    """Distinct thresholds from Risk Score bands - collection priority score is
    risk x exposure, so its scale and meaningful cut points differ from risk alone.
    Derived from the score distribution in notebooks/04_scoring.ipynb (mean ~9.5,
    most mass under 15, tail out to 100)."""
    if collection_priority_score >= 25:
        return "URGENT"
    elif collection_priority_score >= 10:
        return "ELEVATED"
    return "NORMAL"


def evaluate(customer_profile: dict) -> Decision:
    """
    customer_profile expected keys:
        risk_score, risk_band, collection_priority_score, cross_sell_eligible,
        behavioral_score, behavioral_band, health_segment,
        num_late_payments, num_missed_payments, avg_dpd_overall,
        lateness_trend, dpd_trend, utilization_trend
    """
    risk_band = customer_profile["risk_band"]
    collection_priority = _collection_priority_band(customer_profile["collection_priority_score"])
    cross_sell = "ELIGIBLE" if customer_profile["cross_sell_eligible"] else "NOT_ELIGIBLE"
    behavioral_band = customer_profile["behavioral_band"]
    health_segment = customer_profile["health_segment"]

    reason_codes = []
    if customer_profile.get("avg_dpd_overall", 0) and customer_profile["avg_dpd_overall"] > 0:
        reason_codes.append("HIGH_DPD")
    if customer_profile.get("num_missed_payments", 0) and customer_profile["num_missed_payments"] > 0:
        reason_codes.append("MISSED_PAYMENTS")
    if customer_profile.get("lateness_trend", 0) and customer_profile["lateness_trend"] > 0:
        reason_codes.append("WORSENING_PAYMENT_TREND")
    if customer_profile.get("dpd_trend", 0) and customer_profile["dpd_trend"] > 0:
        reason_codes.append("WORSENING_DPD_TREND")
    if customer_profile.get("utilization_trend", 0) and customer_profile["utilization_trend"] > 0:
        reason_codes.append("RISING_UTILIZATION")

    # Priority order matters: collections urgency and hard risk override a cross-sell
    # opportunity even if one is technically present - never recommend selling more
    # credit to someone who needs intervention first.
    if risk_band == "High Risk" or collection_priority == "URGENT":
        recommended_action = "COLLECTION_INTERVENTION"
        if not reason_codes:
            reason_codes.append("HIGH_RISK_SCORE")
    elif risk_band == "Medium Risk":
        recommended_action = "MANUAL_REVIEW"
        if not reason_codes:
            reason_codes.append("MODERATE_RISK_SCORE")
    elif cross_sell == "ELIGIBLE":
        recommended_action = "CROSS_SELL_OPPORTUNITY"
        reason_codes = ["LOW_RISK", "NO_LATE_PAYMENTS", "HEALTHY_UTILIZATION"]
    else:
        recommended_action = "RETENTION_ENGAGEMENT"
        if not reason_codes:
            reason_codes.append("STABLE_LOW_RISK_CUSTOMER")

    return Decision(
        risk_band=risk_band,
        collection_priority=collection_priority,
        cross_sell_opportunity=cross_sell,
        behavioral_band=behavioral_band,
        health_segment=health_segment,
        recommended_action=recommended_action,
        reason_codes=reason_codes,
    )

"""
Customer Health Score — composite of Risk, Behavioral, Collection Severity, and
Cross-Sell Opportunity.

Formula (documented reasoning, not arbitrary weights):
    Health Score
    = 0.40 x (100 - Risk Score)
    + 0.25 x Behavioral Score
    + 0.20 x (100 - Collection Severity)
    + 0.15 x Cross-Sell Opportunity

Weight rationale:
- Risk (40%, inverted): the single biggest driver. A customer likely to default is
  unhealthy regardless of anything else - this mirrors the original project's
  weighting logic (risk mattered most there too).
- Behavioral (25%): a more granular, immediate-term view of actual payment
  discipline, independent of the bureau-score-driven risk model. Meaningful enough
  to be the second-largest weight, but subordinate to the model's own risk read.
- Collection Severity (20%, inverted): risk x exposure. Already partly *derived
  from* Risk, so it gets less independent weight than Risk itself, to avoid
  double-counting the same underlying signal too heavily.
- Cross-Sell Opportunity (15%): a smaller positive adjustment. Being a safe,
  high-value customer should modestly boost the health view, but shouldn't
  outweigh real risk/behavioral signals.

Note: the Godrej brief also mentions an "Engagement/Activity" component. This
dataset has no login/app-usage/interaction log, so that input is not available -
documented here as a genuine data limitation rather than fabricated. See README's
Limitations section.

Band cutoffs (>=80 Healthy, 55-80 Monitor, <55 High Risk) were chosen from the
actual score distribution produced on the full scored portfolio, not round numbers
picked in advance - and validated by a monotonically increasing observed default
rate across bands. See notebooks/04_scoring.ipynb for the validation.
"""
from dataclasses import dataclass

RISK_WEIGHT = 0.40
BEHAVIORAL_WEIGHT = 0.25
COLLECTION_WEIGHT = 0.20
CROSS_SELL_WEIGHT = 0.15

HEALTHY_CUTOFF = 80
MONITOR_CUTOFF = 55


@dataclass
class HealthResult:
    health_score: float
    health_segment: str


def compute_health_score(
    risk_score: float,
    behavioral_score: float,
    collection_severity: float,
    cross_sell_opportunity: float,
) -> float:
    score = (
        RISK_WEIGHT * (100 - risk_score)
        + BEHAVIORAL_WEIGHT * behavioral_score
        + COLLECTION_WEIGHT * (100 - collection_severity)
        + CROSS_SELL_WEIGHT * cross_sell_opportunity
    )
    return round(max(0.0, min(100.0, score)), 1)


def health_segment(health_score: float) -> str:
    if health_score >= HEALTHY_CUTOFF:
        return "Healthy"
    elif health_score >= MONITOR_CUTOFF:
        return "Monitor"
    return "High Risk"


def score_customer(
    risk_score: float, behavioral_score: float, collection_severity: float, cross_sell_opportunity: float
) -> HealthResult:
    score = compute_health_score(risk_score, behavioral_score, collection_severity, cross_sell_opportunity)
    return HealthResult(health_score=score, health_segment=health_segment(score))

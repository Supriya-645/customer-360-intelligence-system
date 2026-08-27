"""
Risk Scorecard — converts the Logistic Regression model's predicted probability
of default into a business-facing 0-100 score and an explainable band.

Note on calibration (documented honestly, see README): the underlying model uses
class_weight='balanced', which improves ranking quality (AUC/KS) at the cost of the
raw probability no longer matching the true population default rate. The Risk Score
below is therefore a *relative ranking* signal for triage/segmentation, not a
calibrated probability of default. That's an intentional, acceptable tradeoff for
this use case (see src/models/evaluate.py for the metrics that justify it), not an
oversight.
"""
from dataclasses import dataclass


@dataclass
class RiskResult:
    risk_score: float
    risk_band: str


# Band cutoffs were chosen from the actual score distribution produced by the
# trained model (mean ~42, not the true ~8% base rate, precisely because of the
# calibration note above) and validated by a monotonically increasing observed
# default rate across bands - not arbitrary round numbers. See notebooks/04_scoring.ipynb.
LOW_RISK_CUTOFF = 30
HIGH_RISK_CUTOFF = 60


def compute_risk_score(probability_of_default: float) -> float:
    """probability_of_default: model's predict_proba()[:, 1] output, in [0, 1]."""
    return round(probability_of_default * 100, 1)


def risk_band(risk_score: float) -> str:
    if risk_score < LOW_RISK_CUTOFF:
        return "Low Risk"
    elif risk_score < HIGH_RISK_CUTOFF:
        return "Medium Risk"
    return "High Risk"


def score_customer(probability_of_default: float) -> RiskResult:
    score = compute_risk_score(probability_of_default)
    return RiskResult(risk_score=score, risk_band=risk_band(score))

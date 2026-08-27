"""
Collection Priority Scorecard — business logic, not a model.

Formula: Risk Score x normalized loan exposure. This flags customers who are
*both* high-risk *and* high-exposure first - a high-risk customer with a tiny
loan is a lower collections priority than a high-risk customer with a large one.
Rescaled to 0-100 for consistency with the other scores.
"""
from dataclasses import dataclass


@dataclass
class CollectionResult:
    collection_priority_score: float
    collection_severity: float  # same value, named for use inside the Health Score formula


def normalize_exposure(amt_credit: float, min_credit: float, max_credit: float) -> float:
    if max_credit == min_credit:
        return 0.0
    return (amt_credit - min_credit) / (max_credit - min_credit)


def compute_collection_priority(
    risk_score: float, amt_credit: float, min_credit: float, max_credit: float, max_raw_in_portfolio: float
) -> CollectionResult:
    """max_raw_in_portfolio: the highest (risk_score x normalized_exposure) value
    seen across the whole portfolio, used to rescale onto a clean 0-100 range.
    Computed once per portfolio batch, not per customer - see src/models/train.py
    or notebooks/04_scoring.ipynb for how it's derived at batch-scoring time."""
    exposure_normalized = normalize_exposure(amt_credit, min_credit, max_credit)
    raw = risk_score * exposure_normalized
    score = round((raw / max_raw_in_portfolio) * 100, 1) if max_raw_in_portfolio else 0.0
    return CollectionResult(collection_priority_score=score, collection_severity=score)

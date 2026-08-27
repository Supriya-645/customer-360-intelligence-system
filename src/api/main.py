"""
Lightweight FastAPI service wiring the feature store -> scorecards -> decision
engine together behind HTTP endpoints.

Deliberately thin: this API does not retrain or re-derive anything - it reads
customer_scores (already computed in notebooks/04_scoring.ipynb / src/models/train.py)
plus the raw behavioral columns needed for the decision engine's reason codes,
and runs the deterministic decision layer per request. No LLM/agent layer sits in
front of the actual risk numbers - see src/decision/decision_engine.py's docstring
for why that separation matters.

Run:
    ./venv/Scripts/python.exe -m uvicorn src.api.main:app --reload
"""
import os
from urllib.parse import quote_plus
from contextlib import asynccontextmanager

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text

from src.scorecards import behavioral_scorecard
from src.decision.decision_engine import evaluate as run_decision_engine

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def get_engine():
    user = os.getenv("POSTGRES_USER", "postgres")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD"))
    return create_engine(f"postgresql+psycopg2://{user}:{password}@localhost:5432/customer360")


engine = get_engine()
app = FastAPI(title="Customer 360 Decision API", version="1.0")


def _fetch_customer_row(customer_id: int) -> dict:
    query = text("SELECT * FROM vw_customer_dashboard WHERE sk_id_curr = :cid")
    with engine.connect() as conn:
        result = conn.execute(query, {"cid": customer_id}).mappings().first()
    if result is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return dict(result)


def _build_scores_and_decision(row: dict) -> dict:
    behavioral = behavioral_scorecard.score_customer(
        total_installments=row.get("total_installments") or 0,
        num_late_payments=row.get("num_late_payments") or 0,
        num_missed_payments=row.get("num_missed_payments") or 0,
        avg_dpd_overall=row.get("avg_dpd_overall") or 0,
        lateness_trend=row.get("lateness_trend") or 0,
        dpd_trend=row.get("dpd_trend") or 0,
        utilization_trend=row.get("utilization_trend") or 0,
    )

    profile = {
        "risk_score": row["risk_score"],
        "risk_band": row["risk_segment"],
        "collection_priority_score": row["collection_priority_score"],
        "cross_sell_eligible": row["cross_sell_eligible"] == "Eligible",
        "behavioral_score": behavioral.behavioral_score,
        "behavioral_band": behavioral.behavioral_band,
        "health_segment": row["health_segment"],
        "num_late_payments": row.get("num_late_payments"),
        "num_missed_payments": row.get("num_missed_payments"),
        "avg_dpd_overall": row.get("avg_dpd_overall"),
        "lateness_trend": row.get("lateness_trend"),
        "dpd_trend": row.get("dpd_trend"),
        "utilization_trend": row.get("utilization_trend"),
    }
    decision = run_decision_engine(profile)
    return {
        "risk_score": row["risk_score"],
        "risk_segment": row["risk_segment"],
        "collection_priority_score": row["collection_priority_score"],
        "collection_rank": row["collection_rank"],
        "cross_sell_eligible": row["cross_sell_eligible"],
        "behavioral_score": behavioral.behavioral_score,
        "behavioral_band": behavioral.behavioral_band,
        "health_score": row["health_score"],
        "health_segment": row["health_segment"],
        "decision": decision.to_dict(),
    }


@app.get("/customers/{customer_id}")
def get_customer(customer_id: int):
    row = _fetch_customer_row(customer_id)
    return {
        "sk_id_curr": row["sk_id_curr"],
        "age_years": row["age_years"],
        "income": row["income"],
        "amt_credit": row["amt_credit"],
        "name_contract_type": row["name_contract_type"],
        "occupation_type": row["occupation_type"],
    }


@app.get("/customers/{customer_id}/scores")
def get_customer_scores(customer_id: int):
    row = _fetch_customer_row(customer_id)
    result = _build_scores_and_decision(row)
    result.pop("decision")
    return result


@app.get("/customers/{customer_id}/decision")
def get_customer_decision(customer_id: int):
    row = _fetch_customer_row(customer_id)
    return _build_scores_and_decision(row)["decision"]


@app.post("/score")
def score_customer_ad_hoc(customer_id: int):
    """POST variant of the scores endpoint - kept as a thin alias so the API
    matches both GET (retrieval) and POST (action-triggering) conventions
    requested in the brief, without duplicating logic."""
    row = _fetch_customer_row(customer_id)
    result = _build_scores_and_decision(row)
    result.pop("decision")
    return result


@app.post("/decision")
def decide_for_customer(customer_id: int):
    row = _fetch_customer_row(customer_id)
    return _build_scores_and_decision(row)["decision"]


@app.get("/portfolio/summary")
def portfolio_summary():
    query = text(
        """
        SELECT
            COUNT(*) AS total_customers,
            SUM(CASE WHEN risk_segment = 'High Risk' THEN 1 ELSE 0 END) AS high_risk_count,
            SUM(CASE WHEN risk_segment = 'Medium Risk' THEN 1 ELSE 0 END) AS medium_risk_count,
            SUM(CASE WHEN risk_segment = 'Low Risk' THEN 1 ELSE 0 END) AS low_risk_count,
            ROUND(AVG(health_score)::numeric, 2) AS avg_health_score,
            SUM(CASE WHEN cross_sell_eligible = 'Eligible' THEN 1 ELSE 0 END) AS cross_sell_opportunities
        FROM customer_scores
        """
    )
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()
    return dict(row)


@app.get("/health")
def health_check():
    return {"status": "ok"}

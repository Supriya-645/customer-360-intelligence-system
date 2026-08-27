"""Centralized configuration - database connection and scorecard thresholds in one
place, so a threshold change doesn't require hunting across multiple files."""
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "customer360")


def sqlalchemy_url() -> str:
    return (
        f"postgresql+psycopg2://{POSTGRES_USER}:{quote_plus(POSTGRES_PASSWORD)}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


def jdbc_url() -> str:
    return f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


# Scorecard thresholds - mirrored from src/scorecards/*.py so they're documented
# in one place too; the scorecard modules remain the source of truth (import
# from there in code), this is a reference/config summary for the README and
# for anyone tuning thresholds without reading every module.
RISK_BANDS = {"Low Risk": (0, 30), "Medium Risk": (30, 60), "High Risk": (60, 100)}
HEALTH_BANDS = {"High Risk": (0, 55), "Monitor": (55, 80), "Healthy": (80, 100)}
CROSS_SELL_RULES = {"max_risk_score": 20, "max_utilization": 0.40, "max_late_payments": 0}

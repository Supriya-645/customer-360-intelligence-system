"""
Integration-style tests against the real customer_features_spark table produced
by src/data/pyspark_pipeline.py. Deliberately queries Postgres directly rather
than spinning up a Spark session per test run (slow, heavyweight for CI) - the
pipeline itself is exercised by actually running it (see README), this just
validates the properties of what it produced.

Skips cleanly if the database isn't reachable (e.g. running tests without
Postgres available), rather than failing tests unrelated to this module.
"""
import os
from urllib.parse import quote_plus

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def _get_engine():
    user = os.getenv("POSTGRES_USER", "postgres")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
    return create_engine(f"postgresql+psycopg2://{user}:{password}@localhost:5432/customer360")


@pytest.fixture(scope="module")
def engine():
    eng = _get_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL not reachable - skipping feature store integration tests")
    return eng


EXPECTED_COLUMNS = {
    "sk_id_curr", "target", "age_years", "employment_years",
    "total_installments", "num_late_payments", "num_missed_payments",
    "lateness_trend", "avg_utilization_overall", "utilization_trend",
    "avg_dpd_overall", "dpd_trend", "num_bureau_accounts", "total_external_debt",
}


def test_expected_columns_exist(engine):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'customer_features_spark'")
        )
        actual_columns = {row[0] for row in result}
    missing = EXPECTED_COLUMNS - actual_columns
    assert not missing, f"customer_features_spark is missing expected columns: {missing}"


def test_no_duplicate_customers(engine):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM (SELECT sk_id_curr FROM customer_features_spark GROUP BY sk_id_curr HAVING COUNT(*) > 1) dup")
        )
        duplicate_count = result.scalar()
    assert duplicate_count == 0


def test_row_count_matches_cleaned_application_table(engine):
    with engine.connect() as conn:
        spark_count = conn.execute(text("SELECT COUNT(*) FROM customer_features_spark")).scalar()
        # stg_application_train already excludes the 4 XNA-gender rows (Phase 5 cleaning);
        # the Spark pipeline applies the same filter independently - counts should match exactly.
        expected_count = conn.execute(text("SELECT COUNT(*) FROM stg_application_train")).scalar()
    assert spark_count == expected_count


def test_target_is_binary(engine):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT target FROM customer_features_spark"))
        values = {row[0] for row in result}
    assert values <= {0, 1}


def test_engineered_features_have_reasonable_null_rate(engine):
    """Not zero nulls (some are expected - see behavioral_scorecard.py's docstring
    on why NULL is meaningful for customers with no card/bureau history), but not
    100% either, which would indicate the join silently failed."""
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM customer_features_spark")).scalar()
        non_null_utilization = conn.execute(
            text("SELECT COUNT(*) FROM customer_features_spark WHERE avg_utilization_overall IS NOT NULL")
        ).scalar()
    assert 0 < non_null_utilization < total

"""
PySpark feature-engineering pipeline for Customer 360.

Purpose (Tessaract 2.0 alignment): demonstrate distributed, scalable customer-level
feature engineering as an alternative/complement to the SQL pipeline in `sql/06_feature_engineering.sql`.
Reads the SAME raw staging tables (loaded by the SQL pipeline) via JDBC, performs
cleaning + Window-function-based trend feature engineering, and writes the result to
a new table `customer_features_spark` in the same PostgreSQL feature store.

Why PySpark here (not Pandas): the raw behavioral tables are large
(installments_payments alone is ~13.6M rows). Pandas holds everything in a single
process's memory; Spark's DataFrame API expresses the same aggregations but can
scale across partitions/executors without a rewrite once the data volume grows
past what fits comfortably in memory on one machine. On this dataset's actual size,
either would technically run - the point is the pipeline is *written* in a way that
scales, not that this specific run needs a cluster.

Run:
    JAVA_HOME=<path to portable JDK> ./venv/Scripts/python.exe -m src.data.pyspark_pipeline
"""
import os
import sys
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JDBC_JAR = os.path.join(PROJECT_ROOT, "tools", "jars", "postgresql-jdbc.jar")


def get_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("Customer360FeatureEngineering")
        .config("spark.jars", JDBC_JAR)
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")  # small cluster-of-one; keep shuffle overhead low
        .getOrCreate()
    )


def jdbc_props():
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return {
        "url": "jdbc:postgresql://localhost:5432/customer360",
        "properties": {"user": user, "password": password, "driver": "org.postgresql.Driver"},
    }


def read_table(spark: SparkSession, table_name: str):
    jdbc = jdbc_props()
    return spark.read.jdbc(url=jdbc["url"], table=table_name, properties=jdbc["properties"])


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean_application(df):
    """Mirrors sql/05_cleaning.sql: fix the DAYS_EMPLOYED anomaly, cap the income
    outlier, drop the handful of XNA-gender rows. Kept consistent with the SQL
    pipeline deliberately, so results are comparable, not just re-invented."""
    df = df.filter(F.col("code_gender") != "XNA")
    df = df.withColumn(
        "days_employed_clean",
        F.when(F.col("days_employed") == 365243, None).otherwise(F.col("days_employed")),
    )
    df = df.withColumn(
        "amt_income_total_clean",
        F.least(F.col("amt_income_total"), F.lit(20000000)),
    )
    return df.dropDuplicates(["sk_id_curr"])


# ---------------------------------------------------------------------------
# Behavioral feature engineering (Window functions)
# ---------------------------------------------------------------------------

def build_payment_features(installments):
    """Payment behaviour: lateness aggregates + recency-split trend, via Window functions.
    Same logic as the SQL version (ROW_NUMBER over each customer's own installment
    history, split into recent/earlier halves), expressed in PySpark's DataFrame API."""
    df = installments.withColumn("days_late", F.col("days_entry_payment") - F.col("days_instalment"))

    w = Window.partitionBy("sk_id_curr").orderBy(F.col("days_instalment").desc())
    w_count = Window.partitionBy("sk_id_curr")

    df = df.withColumn("recency_rank", F.row_number().over(w))
    df = df.withColumn("total_installments_w", F.count("*").over(w_count))

    recent_half = F.col("recency_rank") <= F.col("total_installments_w") / 2

    return df.groupBy("sk_id_curr").agg(
        F.count("*").alias("total_installments"),
        F.sum(F.when(F.col("days_late") > 0, 1).otherwise(0)).alias("num_late_payments"),
        F.sum(F.when(F.col("days_entry_payment").isNull(), 1).otherwise(0)).alias("num_missed_payments"),
        F.avg(F.when(F.col("days_late") > 0, F.col("days_late"))).alias("avg_days_late"),
        F.max("days_late").alias("max_days_late"),
        (
            F.avg(F.when(recent_half & F.col("days_late").isNotNull(), F.col("days_late")))
            - F.avg(F.when(~recent_half & F.col("days_late").isNotNull(), F.col("days_late")))
        ).alias("lateness_trend"),
    )


def build_credit_card_features(credit_card):
    """Credit utilization trend, using MONTHS_BALANCE as the (already comparable)
    time axis - conditional aggregation, same reasoning as the SQL version."""
    df = credit_card.withColumn(
        "utilization",
        F.col("amt_balance") / F.when(F.col("amt_credit_limit_actual") == 0, None).otherwise(F.col("amt_credit_limit_actual")),
    )
    recent = F.col("months_balance") >= -6
    prior = F.col("months_balance").between(-12, -7)

    return df.groupBy("sk_id_curr").agg(
        F.avg("utilization").alias("avg_utilization_overall"),
        (F.avg(F.when(recent, F.col("utilization"))) - F.avg(F.when(prior, F.col("utilization")))).alias(
            "utilization_trend"
        ),
    )


def build_pos_cash_features(pos_cash):
    """DPD trend on POS/cash loans, same MONTHS_BALANCE-based conditional aggregation."""
    recent = F.col("months_balance") >= -6
    prior = F.col("months_balance").between(-12, -7)

    return pos_cash.groupBy("sk_id_curr").agg(
        F.avg("sk_dpd").alias("avg_dpd_overall"),
        F.max("sk_dpd").alias("max_dpd_ever"),
        (F.avg(F.when(recent, F.col("sk_dpd"))) - F.avg(F.when(prior, F.col("sk_dpd")))).alias("dpd_trend"),
    )


def build_bureau_features(bureau):
    """External credit history - plain aggregation, no time series here."""
    return bureau.groupBy("sk_id_curr").agg(
        F.count("*").alias("num_bureau_accounts"),
        F.sum(F.when(F.col("credit_active") == "Active", 1).otherwise(0)).alias("num_active_accounts"),
        F.sum(F.when(F.col("credit_active") == "Closed", 1).otherwise(0)).alias("num_closed_accounts"),
        (-F.min("days_credit")).alias("credit_history_length_days"),
        F.max("credit_day_overdue").alias("max_external_overdue_days"),
        F.sum("amt_credit_sum_debt").alias("total_external_debt"),
    )


def run_pipeline():
    spark = get_spark()
    try:
        application = clean_application(read_table(spark, "raw_application_train"))
        installments = read_table(spark, "raw_installments_payments")
        credit_card = read_table(spark, "raw_credit_card_balance")
        pos_cash = read_table(spark, "raw_pos_cash_balance")
        bureau = read_table(spark, "raw_bureau")

        payment_feats = build_payment_features(installments)
        cc_feats = build_credit_card_features(credit_card)
        pos_feats = build_pos_cash_features(pos_cash)
        bureau_feats = build_bureau_features(bureau)

        base = application.select(
            "sk_id_curr", "target", "name_contract_type", "code_gender",
            "days_birth", "days_employed_clean", "amt_income_total_clean",
            "amt_credit", "amt_annuity", "occupation_type",
            "ext_source_1", "ext_source_2", "ext_source_3",
        )
        base = base.withColumn("age_years", -F.col("days_birth") / 365.0)
        base = base.withColumn("employment_years", -F.col("days_employed_clean") / 365.0)

        result = (
            base
            .join(payment_feats, "sk_id_curr", "left")
            .join(cc_feats, "sk_id_curr", "left")
            .join(pos_feats, "sk_id_curr", "left")
            .join(bureau_feats, "sk_id_curr", "left")
        )

        # Cache before the first action: without this, count() and write() each
        # independently re-execute the whole DAG (including re-reading the 13.6M-row
        # installments table over JDBC), which is both wasteful and, on a plain
        # localhost connection, prone to timing out mid-transfer.
        result = result.cache()

        row_count = result.count()
        print(f"Built customer_features_spark: {row_count} rows, {len(result.columns)} columns")

        jdbc = jdbc_props()
        result.write.jdbc(
            url=jdbc["url"], table="customer_features_spark", mode="overwrite", properties=jdbc["properties"]
        )
        print("Wrote customer_features_spark to PostgreSQL")
        return row_count
    finally:
        spark.stop()


if __name__ == "__main__":
    run_pipeline()

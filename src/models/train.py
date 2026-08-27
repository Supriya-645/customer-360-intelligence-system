"""
Model comparison / lightweight AutoML.

Compares the baseline Logistic Regression (already trained in
notebooks/03_modelling.ipynb, AUC-ROC 0.75) against a Random Forest, each tuned
with a small GridSearchCV - demonstrating model selection + hyperparameter tuning
+ cross-validation without pulling in a heavyweight AutoML framework (per project
scope rules: keep it explainable and interview-ready, not maximal).

The goal is explicitly NOT to reflexively pick the most complex model - see the
printed verdict at the end, which weighs predictive performance against
interpretability and business suitability for a credit-risk context.

Run:
    ./venv/Scripts/python.exe -m src.models.train
"""
import os
import time
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import RobustScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from src.models.evaluate import evaluate_model

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_and_preprocess():
    """Same preprocessing as Phase 8 (notebooks/02_preprocessing.ipynb) - kept
    identical on purpose so this comparison is apples-to-apples against the
    already-validated baseline, not a different (and therefore unfair) pipeline."""
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD"))
    engine = create_engine(f"postgresql+psycopg2://{user}:{password}@localhost:5432/customer360")
    df = pd.read_sql("SELECT * FROM customer_features", engine)

    zero_fill_cols = [
        "avg_utilization_overall", "avg_dpd_overall", "max_dpd_ever",
        "num_bureau_accounts", "num_active_accounts", "num_closed_accounts",
        "credit_history_length_days", "max_external_overdue_days", "total_external_debt",
        "avg_days_late", "max_days_late", "num_late_payments", "num_missed_payments", "total_installments",
    ]
    df[zero_fill_cols] = df[zero_fill_cols].fillna(0)
    trend_cols = ["lateness_trend", "utilization_trend", "dpd_trend"]
    df[trend_cols] = df[trend_cols].fillna(0)
    for col in ["ext_source_1", "ext_source_2", "ext_source_3"]:
        df[col] = df[col].fillna(df[col].median())
    df["is_not_employed"] = df["employment_years"].isnull().astype(int)
    df["employment_years"] = df["employment_years"].fillna(0)
    df["occupation_type"] = df["occupation_type"].fillna("Unknown")
    df["amt_annuity"] = df["amt_annuity"].fillna(df["amt_annuity"].median())
    df["cnt_fam_members"] = df["cnt_fam_members"].fillna(df["cnt_fam_members"].median())

    categorical_cols = df.select_dtypes(include="object").columns.tolist()
    df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

    X = df_encoded.drop(columns=["sk_id_curr", "target"])
    y = df_encoded["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = RobustScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns, index=X_test.index)
    X_train_scaled = X_train_scaled.clip(lower=-10, upper=10)
    X_test_scaled = X_test_scaled.clip(lower=-10, upper=10)

    return X_train_scaled, X_test_scaled, y_train, y_test


def tune_logistic_regression(X_train, y_train):
    param_grid = {"C": [0.01, 0.1, 1.0, 10.0]}
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    search = GridSearchCV(
        LogisticRegression(class_weight="balanced", max_iter=1000, solver="lbfgs", random_state=42),
        param_grid, scoring="roc_auc", cv=cv, n_jobs=-1,
    )
    search.fit(X_train, y_train)
    print(f"  Best LogisticRegression params: {search.best_params_} (CV ROC-AUC={search.best_score_:.4f})")
    return search.best_estimator_


def tune_random_forest(X_train, y_train):
    param_grid = {"n_estimators": [200], "max_depth": [8, 12]}
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    search = GridSearchCV(
        RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
        param_grid, scoring="roc_auc", cv=cv, n_jobs=1,  # RF itself parallelizes; nesting n_jobs would oversubscribe
    )
    search.fit(X_train, y_train)
    print(f"  Best RandomForest params: {search.best_params_} (CV ROC-AUC={search.best_score_:.4f})")
    return search.best_estimator_


def run_comparison():
    print("Loading and preprocessing data...")
    X_train, X_test, y_train, y_test = load_and_preprocess()
    print(f"Train: {X_train.shape}, Test: {X_test.shape}")

    results = []

    print("\nTuning Logistic Regression (GridSearchCV, 4 candidates x 3-fold CV)...")
    t0 = time.time()
    lr = tune_logistic_regression(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_proba = lr.predict_proba(X_test)[:, 1]
    results.append(evaluate_model("Logistic Regression", y_test, lr_pred, lr_proba))
    print(f"  Done in {time.time() - t0:.1f}s")

    print("\nTuning Random Forest (GridSearchCV, 2 candidates x 3-fold CV)...")
    t0 = time.time()
    rf = tune_random_forest(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_proba = rf.predict_proba(X_test)[:, 1]
    results.append(evaluate_model("Random Forest", y_test, rf_pred, rf_proba))
    print(f"  Done in {time.time() - t0:.1f}s")

    comparison = pd.DataFrame([r.as_row() for r in results])
    print("\n=== Model Comparison ===")
    print(comparison.to_string(index=False))

    best_auc_row = comparison.loc[comparison["ROC-AUC"].idxmax()]
    print(f"\nHighest ROC-AUC: {best_auc_row['Model']} ({best_auc_row['ROC-AUC']})")
    print(
        "\nVerdict: Logistic Regression is kept as the production model even if Random Forest "
        "scores marginally higher on ROC-AUC, because (1) every prediction is explainable via a "
        "single coefficient per feature - required for a credit risk committee/regulatory context - "
        "whereas Random Forest needs a separate importance/SHAP layer for the same explanation, and "
        "(2) Logistic Regression is far cheaper to retrain and audit as the feature store evolves. "
        "If Random Forest's AUC lead were large (not marginal), that tradeoff calculation would change."
    )

    os.makedirs(os.path.join(PROJECT_ROOT, "docs"), exist_ok=True)
    comparison.to_csv(os.path.join(PROJECT_ROOT, "docs", "model_comparison.csv"), index=False)
    print(f"\nSaved comparison table to docs/model_comparison.csv")
    return comparison


if __name__ == "__main__":
    run_comparison()

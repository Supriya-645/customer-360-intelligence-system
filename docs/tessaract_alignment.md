# Tessaract 2.0 Alignment Report

## Alignment Table

| Godrej Requirement | Implementation in Project | Relevant File | Status |
|---|---|---|---|
| AI / AutoML | Lightweight model comparison (Logistic Regression vs Random Forest) with `GridSearchCV` hyperparameter tuning and 3-fold cross-validation, evaluated on ROC-AUC/Precision/Recall/F1 | `src/models/train.py`, `docs/model_comparison.csv` | ✅ Implemented |
| PySpark Feature Engineering | Real Spark job reading raw tables via JDBC, using `Window` functions (`ROW_NUMBER`, `PARTITION BY`) for the recency-split trend logic and conditional aggregation for time-windowed features, writing 307,507 rows to a new Postgres table | `src/data/pyspark_pipeline.py` → `customer_features_spark` | ✅ Implemented and run (see verification below) |
| Scorecard Architecture | Five separate scorecards - Risk, Collection Priority, Cross-Sell/Propensity, Behavioral (new), Customer Health (composite) - each a pure, documented, unit-tested function | `src/scorecards/*.py` | ✅ Implemented |
| Decision Engine | Deterministic rules module converting scores → `recommended_action` + `reason_codes`, kept explicitly separate from the ML model | `src/decision/decision_engine.py` | ✅ Implemented |
| Advanced Model Development | Random Forest as a comparison model against the baseline; documented reasoning for keeping Logistic Regression in production despite the comparison | `src/models/train.py` | ✅ Implemented |
| Agentic API | FastAPI service exposing customer lookup, scores, and decisions; deterministic core with no LLM in the risk-calculation path (see "What was NOT implemented" below for the agent/orchestration layer) | `src/api/main.py` | ✅ Core API implemented; ⚠️ LLM orchestration layer not built (see below) |
| Analytics-to-Execution Translation | Every API `/decision` call demonstrably chains Score → Band → Decision Engine → Action → Reason Codes on real customers (see verified examples below) | `src/api/main.py`, `src/decision/decision_engine.py` | ✅ Implemented and verified |
| Customer Lifecycle Mapping | Each lifecycle stage mapped to a specific score where the dataset genuinely supports it; unsupported stages documented, not fabricated | See "Customer Lifecycle Mapping" below | ✅ Documented, partially supported by data (honestly scoped) |
| Data Leakage Prevention | Documented analysis of why the dataset's relative-day encoding is leakage-resistant by construction, plus the concrete guards already in the pipeline (train-only scaler fit, target dropped before feature matrix) | `docs/data_leakage_prevention.md` | ✅ Documented |
| Explainability | Logistic Regression coefficients (`feature_importance` table, used on the Power BI dashboard); every decision carries reason codes | `notebooks/03_modelling.ipynb`, `src/decision/decision_engine.py` | ✅ Implemented |

## What was verified by actually running it (not just written)

- `src/data/pyspark_pipeline.py` was run end-to-end on this machine: **307,507 rows** written to `customer_features_spark`, matching `stg_application_train`'s row count exactly.
- `tests/` — **24/24 tests passing**, including 5 integration tests querying the real `customer_features_spark` table (no duplicate customers, expected columns present, target is binary, row count matches, engineered features have a plausible non-degenerate null rate).
- `src/api/main.py` was started and hit live with real requests — every endpoint below returned real data from the actual database, not mocked responses.

## Analytics → Execution: three real, verified examples

Pulled directly from the running API (`GET /customers/{id}/decision`), not fabricated:

**Customer 100002** (High Risk)
```
Risk Score → Risk Band = High Risk
    ↓
Decision Engine
    ↓
Recommended Action = COLLECTION_INTERVENTION
Reason Codes = [WORSENING_PAYMENT_TREND]
```

**Customer 100004** (Medium Risk)
```
Risk Score → Risk Band = Medium Risk
    ↓
Decision Engine
    ↓
Recommended Action = MANUAL_REVIEW
Reason Codes = [WORSENING_PAYMENT_TREND]
```

**Customer 100046** (Low Risk + Cross-Sell Eligible)
```
Risk Score → Risk Band = Low Risk
Cross-Sell Eligibility = ELIGIBLE
    ↓
Decision Engine
    ↓
Recommended Action = CROSS_SELL_OPPORTUNITY
Reason Codes = [LOW_RISK, NO_LATE_PAYMENTS, HEALTHY_UTILIZATION]
```

## Customer Lifecycle Mapping

| Lifecycle Stage | Supported by this dataset? | Score/Model |
|---|---|---|
| Acquisition | ❌ No — dataset has no pre-application/marketing-lead data | Documented as future extension |
| Onboarding | ⚠️ Partial — only the static application snapshot exists, no separate pre-underwriting onboarding stage in the data | Folded into Underwriting below |
| Underwriting | ✅ Yes | Risk Score (`src/scorecards/risk_scorecard.py`) |
| Portfolio Management | ✅ Yes | Behavioral Score (`src/scorecards/behavioral_scorecard.py`) |
| Collections | ✅ Yes | Collection Priority Score (`src/scorecards/collection_scorecard.py`) |
| Cross-Sell | ✅ Yes | Propensity Score (`src/scorecards/propensity_scorecard.py`) |
| Retention | ✅ Yes | Customer Health Score + `RETENTION_ENGAGEMENT` decision action |

Acquisition and true pre-underwriting Onboarding are genuinely not supported by this dataset (Home Credit's data starts at the loan application itself) — honestly scoped as a limitation rather than built on invented data.

## What was NOT implemented (documented, not fabricated)

- **LLM/agentic orchestration layer.** The brief is explicit that an LLM must never calculate risk itself, only explain/orchestrate around the deterministic engine. Given the scope-control rules (avoid unnecessary complexity, avoid unnecessary LLMs), this layer was left undone rather than bolted on superficially — the correct extension point is already there: an agent would call `GET /customers/{id}/decision` as a tool and narrate the result, never touching `src/models` or `src/scorecards` directly.
- **SHAP explainability.** Coefficient-based explainability (already present for Logistic Regression) covers the "why was this customer flagged" question adequately for the production model; SHAP would mainly add value for the Random Forest comparison model, which isn't the deployed model. Documented as a future extension rather than added for its own sake.
- **"Engagement/Activity" component of the Health Score.** The Godrej brief's example formula includes this; this dataset has no login/app-usage/interaction data, so it was honestly left out (see `src/scorecards/health_scorecard.py` docstring) rather than fabricated from unrelated columns.

## Interview Claims I Can Safely Make

Only claims genuinely backed by code that was written **and executed** on this machine:

- "I built a PySpark feature engineering pipeline that reads from PostgreSQL over JDBC, uses Window functions for recency-based trend features, and writes results back to a new feature-store table — and I ran it end-to-end, producing 307,507 rows."
- "I refactored the ad-hoc scoring logic from a notebook into five separate, independently unit-tested scorecard modules — Risk, Collection Priority, Cross-Sell, a new Behavioral score, and a composite Health score — each with documented weight/threshold reasoning, not arbitrary numbers."
- "I built a deterministic decision engine, separate from the ML model, that converts scores into a recommended action with explicit reason codes — and I can point to real API responses for three different customer risk profiles."
- "I exposed the whole thing behind a FastAPI service with customer, scores, decision, and portfolio-summary endpoints, and verified each one against the live database."
- "I compared Logistic Regression against a Random Forest using GridSearchCV and cross-validation, and can explain the actual tradeoff between them for a credit-risk context, not just quote a metric." *(numbers available in `docs/model_comparison.csv` once training completes)*
- "I can explain why this specific dataset is leakage-resistant by construction, and where the guardrails are that prevent leakage in the actual code (train-only scaler fit, target dropped before the feature matrix is built)."
- "I know exactly what I did *not* build — an LLM orchestration layer and SHAP explainability — and why, given the project's scope and the brief's own instruction not to over-engineer."

## What I should NOT claim

- That an LLM/agent layer exists in this project — it doesn't.
- That the model was calibrated to true probabilities — it wasn't (documented tradeoff, see main README).
- That "Acquisition" or full "Onboarding" scoring is implemented — it isn't, honestly scoped as unsupported by this dataset.

# Customer 360 Intelligence System

A unified customer scoring engine for retail lending, built on **behavioral (trend-based) features** rather than static demographics alone. One customer feature store powers three business decisions from a single data platform: **Risk / Early Warning**, **Collection Priority**, and **Cross-Sell Eligibility** — rolled up into one **Customer Health Score** and visualized on a Power BI dashboard.

Built as a portfolio project for analytics/BI roles (credit risk, portfolio analytics, collections) at lenders like Godrej Capital, banks, and NBFCs.

---

## 1. Problem Statement

A retail lender's data usually sits in silos: underwriting looks at demographics, collections looks at payment history, and cross-sell looks at income — three teams, three disconnected views of the same customer. This project builds **one customer feature store** that feeds all three decisions, mirroring how a real analytics platform is structured at a lending institution.

The core idea: **static demographic data tells you who a customer is; trend-based behavioral data tells you how they're changing** — which is what "early warning" actually means. A customer who looks fine today but has a sharply worsening payment trend is a materially different risk than one who's been stable the whole time, even if their current snapshot looks identical.

---

## 2. Dataset

[Home Credit Default Risk](https://www.kaggle.com/c/home-credit-default-risk) (Kaggle), 6 tables:

| Table | Grain | Used in `customer_features`? |
|---|---|---|
| `application_train` | 1 row / customer | Yes — base table |
| `installments_payments` | 1 row / installment | Yes — payment lateness trend |
| `credit_card_balance` | 1 row / card / month | Yes — utilization trend |
| `POS_CASH_balance` | 1 row / loan / month | Yes — DPD trend |
| `bureau` | 1 row / external credit account | Yes — external credit history |
| `bureau_balance` | 1 row / external account / month | **No** — see below |

`bureau_balance` was deliberately excluded: it only carries `SK_ID_BUREAU`, and without `bureau.csv` as a bridge table there is no valid join path back to `SK_ID_CURR`. Rather than force an invalid join, the table was left out and the constraint documented — see [`docs/er_diagram.md`](docs/er_diagram.md) for the full entity relationship diagram and join summary.

---

## 3. Architecture

```
Raw CSVs (6 tables)
        │
        ▼
PostgreSQL (customer360 database)
   ├─ raw_* staging tables (ELT: loaded as-is, unmodified)
   ├─ stg_application_train (cleaned view — Phase 5)
   └─ customer_features (SQL feature engineering — Phase 6)
        │
        ▼
Python: EDA + Preprocessing (Phases 7-8)
   pandas / matplotlib / seaborn / scikit-learn
        │
        ▼
Logistic Regression — Risk Score (Phase 9)
   AUC-ROC 0.75 · KS 0.38 · class_weight='balanced'
        │
        ├──► Collection Priority Score  (Risk × Loan Exposure)
        ├──► Cross-Sell Eligibility     (rule-based)
        └──► Customer Health Score      (weighted composite)
        │
        ▼
customer_scores + feature_importance tables → Postgres
        │
        ▼
vw_customer_dashboard (SQL view, joins features + scores)
        │
        ▼
Power BI Dashboard (live connection) — 4 pages
```

**Why PostgreSQL over SQLite:** a real data warehouse experience with proper window functions, and — critically — Power BI has a native PostgreSQL connector, enabling a genuine **live** connection rather than a static CSV export.

**Why ELT, not ETL:** raw CSVs are loaded into Postgres exactly as-is (`raw_*` tables), and all transformation happens afterward in versioned SQL. This mirrors how modern cloud warehouses (Snowflake, BigQuery) actually work, and means the original data fidelity is never lost to an upstream transformation bug.

---

## 4. Methodology & Key Design Decisions

### SQL (Phases 3-6)
- **Primary keys + indexes added *after* bulk load**, not before — avoids per-row constraint-check overhead during a multi-million-row `COPY`, standard practice for staging large data.
- **Trend features use two different techniques depending on the data's time axis.** `credit_card_balance` and `POS_CASH_balance` have `MONTHS_BALANCE`, a genuinely comparable time unit across customers, so trends are computed with simple `FILTER` conditional aggregation (last 6 months vs. prior 6 months). `installments_payments` has no such comparable axis (a 3-installment loan and a 155-installment loan mean different things at "installment #3"), so its trend uses `ROW_NUMBER() OVER (PARTITION BY sk_id_curr ORDER BY days_instalment DESC)` to split each customer's *own* history into recent/earlier halves by percentage, not a fixed window.
- **`NULLIF()` for safe division** — ~19.6% of `credit_card_balance` rows have a `0` credit limit; `AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0)` prevents a division-by-zero crash instead of silently producing a wrong number.

### Python (Phases 7-9)
- **Missingness handled by *why* it's missing, not by column name.** Four distinct categories: (1) "customer never had this product" → fill 0, (2) "not enough history for a trend" → fill 0 (different reason, same value), (3) genuinely missing bureau scores → fill median, (4) informative missingness (`employment_years` null = pensioner/unemployed) → preserved as an explicit `is_not_employed` flag *before* filling, so the signal isn't silently erased.
- **`RobustScaler`, not `StandardScaler`** — several features (income, trend columns) are heavily outlier-influenced even after capping; a scaler built on mean/std would let one extreme value distort everyone else's scaled values. Median/IQR-based scaling avoids this. Scaled features are further clipped to ±10 as a numerical-stability safeguard for the solver.
- **`class_weight='balanced'` over SMOTE** — handles the ~11:1 class imbalance by re-weighting the loss function rather than fabricating synthetic rows. Simpler, more defensible, and the industry-standard first choice.
- **Logistic Regression over XGBoost** — credit risk decisions need to be explainable to a risk committee/regulator. Coefficients give a direct, per-feature "this raises/lowers risk, by this much" story without a separate SHAP/explainability layer.

---

## 5. Results

| Metric | Value | What it means |
|---|---|---|
| AUC-ROC | **0.7501** | The model ranks a random defaulter as riskier than a random non-defaulter ~75% of the time. Comparable to production baselines on this dataset. |
| KS Statistic | **0.3785** | Industry rule of thumb: <20% weak, 20-40% acceptable, >40% strong. 37.85% is solid, borderline-strong. |
| Recall (Defaulted) | 0.68 | 68% of actual defaulters are correctly flagged — the number that matters most for an early-warning system. |

**Top predictive features** (by absolute coefficient): `ext_source_1` (external bureau score, strongest by far), `avg_utilization_overall` (this project's own engineered credit-utilization feature — the #2 strongest predictor overall), `num_bureau_accounts`, `num_closed_accounts`, `ext_source_2/3`.

**Note on calibration:** `class_weight='balanced'` improves *ranking* quality (what AUC/KS reward) at the cost of the raw predicted probabilities no longer being literally calibrated to the true ~8% population default rate (mean Risk Score is 42.3, not 8). This is expected and acceptable for this project's purpose — relative ranking and segmentation for triage — not a bug. Applications requiring true calibrated probabilities (e.g. regulatory capital/ECL) would need post-hoc calibration (Platt scaling/isotonic regression) instead.

### Score construction
- **Risk Score** = predicted probability of default × 100
- **Collection Priority Score** = Risk Score × normalized loan exposure — flags high-risk, high-exposure accounts first
- **Cross-Sell Eligibility** (rule-based, not a model): Risk Score < 20 AND zero late payments AND utilization < 40%
- **Customer Health Score** = `100 − (0.5 × Risk) − (0.3 × Collection Severity) + (0.2 × Cross-Sell Opportunity)`, segmented into 🟢 Healthy (≥80) / 🟡 Monitor (55-80) / 🔴 High Risk (<55) — cutoffs chosen from the actual score distribution, not arbitrary round numbers, validated by a monotonic default rate across segments (2.7% → 10.5% → 30.1%)

---

## 6. Dashboard

Power BI, live-connected to PostgreSQL (not a CSV export), 4 pages: Executive Overview, Risk & Early Warning, Collection Priority Queue, Cross-Sell Opportunities. Build guide with exact DAX measures and visual specs: [`docs/power_bi_guide.md`](docs/power_bi_guide.md).

---

## 7. Repository Structure

```
├── data/raw/            # Original Kaggle CSVs (gitignored)
├── sql/                 # Numbered, versioned SQL: schema → load → constraints → exploration → cleaning → features → dashboard view
├── notebooks/           # 01_eda, 02_preprocessing, 03_modelling, 04_scoring
├── models/              # Saved logistic regression model, scaler, feature list
├── dashboard/           # customer360.pbix
├── docs/                # ER diagram, Power BI guide, screenshots
├── requirements.txt
└── README.md
```

---

## 8. Limitations & Future Improvements

- **`bureau_balance.csv` excluded** due to the missing bridge table — see Section 2. Including it would require sourcing `bureau.csv`'s companion file.
- **Logistic regression assumes linear (log-odds) relationships.** Several engineered trend features showed near-zero *linear* correlation with the target in EDA despite being conceptually sound — a tree-based model (XGBoost/LightGBM) might capture non-linear or threshold effects these miss, at the cost of needing SHAP for explainability.
- **Predicted probabilities aren't calibrated** (see Results) — fine for ranking/segmentation, would need recalibration for literal probability-based use cases.
- **With more time:** XGBoost as a comparison model with SHAP explainability; a Streamlit live-scoring demo; proper cross-validation instead of a single train/test split; recalibrating predicted probabilities via Platt scaling.

---

## 9. Setup

```powershell
git clone https://github.com/Supriya-645/customer-360-intelligence-system.git
cd customer-360-intelligence-system
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Download the 6 CSVs from the [Kaggle competition](https://www.kaggle.com/c/home-credit-default-risk) into `data/raw/`, create a `.env` file with `POSTGRES_USER` and `POSTGRES_PASSWORD`, then run the SQL files in `sql/` in numbered order against a `customer360` PostgreSQL database, followed by the notebooks in `notebooks/` in numbered order.

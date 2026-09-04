# Customer 360 Intelligence System

A Customer 360 Risk, Scorecard, and Decision Intelligence Platform for retail lending — combining **SQL and PySpark feature engineering**, an **interpretable Logistic Regression risk model** (benchmarked against Random Forest), a **five-scorecard business layer** (Risk, Collection Priority, Cross-Sell, Behavioral, and composite Health), a **deterministic decision engine**, a **FastAPI service**, and a **live-connected Power BI dashboard**.

The system ingests raw loan application, payment, credit card, POS/cash loan, and bureau data, engineers behavioral trend features using SQL and PySpark window functions, trains an interpretable risk model, derives Collection Priority, Cross-Sell, and Behavioral scores through auditable business logic, rolls everything into a composite Customer Health Score, routes it through a deterministic decision engine, and surfaces it all on a live Power BI dashboard and a FastAPI service.

---

## 🚀 Features

### 🗄️ Data Warehouse & Feature Engineering

* PostgreSQL data warehouse built on an **ELT** pattern — raw data loaded as-is, all transformation versioned in SQL
* Primary keys, indexes, and constraints added post-load for bulk-insert performance
* Data cleaning layer handling anomalous placeholder values, invalid categories, and outlier capping
* **PySpark pipeline** reading the same raw tables over JDBC, using `Window` functions for distributed, scalable trend-feature engineering as an alternative to the SQL pipeline

### 📈 Behavioral Feature Engineering

* Trend features built with SQL and PySpark **window functions** (`ROW_NUMBER`, `PARTITION BY`, `FILTER`-based conditional aggregation)
* Payment lateness trend, credit utilization trend, DPD (days-past-due) trend
* External bureau history: active/closed accounts, credit history length, external debt exposure

### 🔍 Exploratory Data Analysis

* Missing-value analysis categorized by *cause*, not just column
* Distribution analysis with outlier-aware visualization
* Correlation analysis against target and cross-table feature validation
* Class imbalance diagnostics

### 🧮 Risk Prediction Model

* Logistic Regression with class-weighted loss for imbalance handling
* Robust scaling resistant to outlier-heavy financial features
* Coefficient-level explainability — every prediction traceable to a specific feature and direction
* **Model comparison layer** — Random Forest tuned via `GridSearchCV` + cross-validation, benchmarked against the baseline on ROC-AUC/KS/Precision/Recall/F1

### 🎯 Scorecard Layer

No black boxes here — pure, auditable, unit-tested business logic on top of the model:

* **Risk Score** — model probability rescaled to 0-100
* **Collection Priority Score** — risk × loan exposure
* **Cross-Sell Propensity Score** — rule-based approval logic
* **Behavioral Score** *(new)* — payment discipline summarized directly from transaction history, independent of bureau-driven risk
* **Customer Health Score** — weighted composite of all four, segmented into Healthy / Monitor / High Risk

### ⚖️ Decision Engine

* Deterministic rules layer converting scores into business actions — kept explicitly separate from the ML model
* Every decision carries explainable `reason_codes` (e.g. `HIGH_DPD`, `WORSENING_PAYMENT_TREND`)
* Routes: `COLLECTION_INTERVENTION`, `MANUAL_REVIEW`, `CROSS_SELL_OPPORTUNITY`, `RETENTION_ENGAGEMENT`

### 🌐 API

* FastAPI service exposing customer profile, scores, and decisions
* Thin serving layer — reads already-computed scores, runs the decision engine per request, no retraining at request time

### 📊 Power BI Dashboard

* **Live** PostgreSQL connection — not a static CSV export
* Custom DAX measures for portfolio-level KPIs
* 4 dedicated pages:

  * Executive Overview
  * Risk & Early Warning
  * Collection Priority Queue
  * Cross-Sell Opportunities

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    A[Raw CSVs - 6 tables] --> B[PostgreSQL Warehouse<br/>raw staging tables]
    B --> C1[SQL Feature Engineering<br/>window functions, CTEs]
    B --> C2[PySpark Feature Engineering<br/>JDBC read, Window functions]
    C1 --> D1[customer_features]
    C2 --> D2[customer_features_spark]
    D1 --> E[Python EDA and Preprocessing]
    E --> F1[Logistic Regression<br/>production model, AUC-ROC 0.75]
    E --> F2[Random Forest<br/>comparison model, GridSearchCV]
    F1 --> G[Scorecard Layer]
    G --> G1[Risk Score]
    G --> G2[Collection Priority Score]
    G --> G3[Cross-Sell Propensity Score]
    G --> G4[Behavioral Score]
    G1 --> G5[Customer Health Score]
    G2 --> G5
    G3 --> G5
    G4 --> G5
    G5 --> H[Decision Engine<br/>deterministic rules and reason codes]
    H --> I[FastAPI Service]
    G5 --> J[customer_scores table]
    J --> K[vw_customer_dashboard]
    K --> L[Power BI Dashboard - live]
    I --> L
```

---

## 🛠️ Tech Stack

### Data Warehouse & Engineering

* PostgreSQL
* SQL (window functions, CTEs, views)
* PySpark

### Processing & Modelling

* Python
* pandas / NumPy
* SQLAlchemy
* scikit-learn (Logistic Regression, Random Forest, `GridSearchCV`)

### API

* FastAPI
* uvicorn

### Visualization

* Power BI
* DAX

### Testing & Tooling

* pytest
* Jupyter Notebook
* Git / GitHub
* python-dotenv

---

## 📁 Project Structure

```text
customer-360-intelligence-system/
│
├── data/
│   └── raw/
│       └── # Original Kaggle CSVs (gitignored)
│
├── sql/
│   ├── 01_schema.sql
│   ├── 02_load_data.sql
│   ├── 03_constraints_indexes.sql
│   ├── 04_exploration.sql
│   ├── 05_cleaning.sql
│   ├── 06_feature_engineering.sql
│   └── 07_dashboard_view.sql
│
├── src/
│   ├── data/pyspark_pipeline.py        # PySpark feature engineering (JDBC, Window functions)
│   ├── scorecards/                     # Risk, Collection, Propensity, Behavioral, Health
│   ├── decision/decision_engine.py     # Deterministic rules + reason codes
│   ├── models/                         # train.py (model comparison), evaluate.py
│   ├── api/main.py                     # FastAPI service
│   └── config/settings.py
│
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_preprocessing.ipynb
│   ├── 03_modelling.ipynb
│   └── 04_scoring.ipynb
│
├── tests/                              # pytest - scorecards, decision engine, feature store
│
├── models/
│   ├── logistic_regression_model.pkl
│   ├── robust_scaler.pkl
│   └── feature_columns.pkl
│
├── dashboard/
│   └── customer360.pbix
│
├── docs/
│   ├── er_diagram.md
│   ├── power_bi_guide.md
│   ├── data_leakage_prevention.md
│   ├── tessaract_alignment.md
│   ├── model_comparison.csv
│   └── screenshots/
│
├── requirements.txt
└── README.md
```

---

## ⚙️ Workflow

**Step 1** — Load raw CSVs into PostgreSQL staging tables

↓

**Step 2** — Add constraints and indexes

↓

**Step 3** — Explore and clean data in SQL

↓

**Step 4** — Engineer behavioral trend features with SQL and PySpark window functions

↓

**Step 5** — Build `customer_features` (and `customer_features_spark`) — one row per customer

↓

**Step 6** — Run EDA in Python (missing values, distributions, correlations, imbalance)

↓

**Step 7** — Preprocess: imputation, encoding, scaling, train/test split

↓

**Step 8** — Train and evaluate the Logistic Regression risk model; benchmark against Random Forest

↓

**Step 9** — Derive Risk, Collection Priority, Cross-Sell, Behavioral, and Health scores

↓

**Step 10** — Save scores back to PostgreSQL

↓

**Step 11** — Route scores through the deterministic decision engine

↓

**Step 12** — Expose everything via FastAPI

↓

**Step 13** — Connect Power BI live to the database and build the 4-page dashboard

---

## 📊 Dashboard Features

* Executive KPI strip — portfolio size, exposure, at-risk count, average health score
* Risk score distribution and behavioral trend breakdown by segment
* Top risk-driving features, straight from model coefficients
* Collection priority queue ranked by risk × exposure
* DPD bucket breakdown
* Cross-sell eligible segment view

---

## 🧪 Testing

`./venv/Scripts/python.exe -m pytest tests/ -v` — 24 tests covering scorecard edge cases, decision engine routing for every risk/collection/cross-sell combination, and integration checks against the real `customer_features_spark` table.

---

## 📈 Future Improvements

* SHAP-based explainability for the Random Forest comparison model
* LLM/agentic orchestration layer calling the decision engine as a tool (not calculating risk itself)
* Streamlit live-scoring demo for single-customer what-if analysis
* Probability calibration (Platt scaling / isotonic regression)
* Automated data refresh pipeline
* CI checks for SQL/notebook/test execution

Full scope decisions and reasoning: [`docs/tessaract_alignment.md`](docs/tessaract_alignment.md).

---

## 👩‍💻 Author

**Supriya Patil**

Data Analytics | SQL | Python | PySpark | Power BI | Credit Risk Modelling

---

## 📄 License

This project is intended for educational and portfolio purposes.

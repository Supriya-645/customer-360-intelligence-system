# Customer 360 Intelligence System

A unified customer scoring engine for retail lending that combines **SQL-based behavioral feature engineering**, **Logistic Regression risk modelling**, **rule-based business scoring**, and a **live-connected Power BI dashboard** to power three lending decisions — Risk, Collections, and Cross-Sell — from a single customer feature store.

The system ingests raw loan application, payment, credit card, POS/cash loan, and bureau data, engineers behavioral trend features using SQL window functions, trains an interpretable risk model, derives Collection Priority and Cross-Sell scores through business logic, rolls everything into a composite Customer Health Score, and surfaces it all on a live Power BI dashboard.

---

## 🚀 Features

### 🗄 Data Warehouse & SQL Engineering
- PostgreSQL data warehouse built on an **ELT** pattern — raw data loaded as-is, all transformation versioned in SQL
- Primary keys, indexes, and constraints added post-load for bulk-insert performance
- Data cleaning layer handling anomalous placeholder values, invalid categories, and outlier capping

### 📈 Behavioral Feature Engineering
- Trend features built with SQL **window functions** (`ROW_NUMBER`, `PARTITION BY`, `FILTER`-based conditional aggregation)
- Payment lateness trend, credit utilization trend, DPD (days-past-due) trend
- External bureau history: active/closed accounts, credit history length, external debt exposure

### 🔍 Exploratory Data Analysis
- Missing-value analysis categorized by *cause*, not just column
- Distribution analysis with outlier-aware visualization
- Correlation analysis against target and cross-table feature validation
- Class imbalance diagnostics

### 🧮 Risk Prediction Model
- Logistic Regression with class-weighted loss for imbalance handling
- Robust scaling resistant to outlier-heavy financial features
- Coefficient-level explainability — every prediction traceable to a specific feature and direction

### 🎯 Business Scoring Layer
No black boxes here — pure, auditable business logic on top of the model:
- **Risk Score** — model probability rescaled to 0-100
- **Collection Priority Score** — risk × loan exposure
- **Cross-Sell Eligibility** — rule-based approval logic
- **Customer Health Score** — weighted composite of all three, segmented into Healthy / Monitor / High Risk

### 📊 Power BI Dashboard
- **Live** PostgreSQL connection — not a static CSV export
- Custom DAX measures for portfolio-level KPIs
- 4 dedicated pages: Executive Overview, Risk & Early Warning, Collection Priority Queue, Cross-Sell Opportunities

---

## 🏗 System Architecture

## 🏗 System Architecture

```mermaid
flowchart TD
    A[Raw CSVs - 6 tables] --> B[PostgreSQL Warehouse<br/>raw staging to cleaned views]
    B --> C[SQL Feature Engineering Layer<br/>window functions, CTEs, trend features]
    C --> D[customer_features]
    D --> E[Python EDA and Preprocessing<br/>pandas / scikit-learn]
    E --> F[Logistic Regression Model<br/>Risk Score, coefficient-level explainability]
    F --> G[Collection Priority Score<br/>risk x loan exposure]
    F --> H[Cross-Sell Eligibility<br/>rule-based]
    F --> I[Customer Health Score<br/>composite]
    G --> J[customer_scores table - PostgreSQL]
    H --> J
    I --> J
    J --> K[vw_customer_dashboard - SQL view]
    K --> L[Power BI Dashboard - live connection]

---

## 🛠 Tech Stack

**Data Warehouse**
- PostgreSQL
- SQL (window functions, CTEs, views)

**Processing & Feature Engineering**
- Python
- pandas
- NumPy
- SQLAlchemy

**Machine Learning**
- scikit-learn
- Logistic Regression
- RobustScaler

**Visualization**
- Power BI
- DAX

**Environment & Tooling**
- Jupyter Notebook
- Git / GitHub
- python-dotenv

---

## 📁 Project Structure

customer-360-intelligence-system/
│
├── data/
│   └── raw/                  # Original Kaggle CSVs (gitignored)
│
├── sql/
│   ├── 01_schema.sql
│   ├── 02_load_data.sql
│   ├── 03_constraints_indexes.sql
│   ├── 04_exploration.sql
│   ├── 05_cleaning.sql
│   ├── 06_feature_engineering.sql
│   └── 07_dashboard_view.sql
│├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_preprocessing.ipynb
│   ├── 03_modelling.ipynb
│   └── 04_scoring.ipynb
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
│   └── screenshots/
│
├── requirements.txt
└── README.md


---

## ⚙️ Workflow

**Step 1**
Load raw CSVs into PostgreSQL staging tables

↓

**Step 2**
Add constraints and indexes

↓

**Step 3**
Explore and clean data in SQL

↓

**Step 4**
Engineer behavioral trend features with window functions

↓

**Step 5**
Build `customer_features` — one row per customer

↓

**Step 6**
Run EDA in Python (missing values, distributions, correlations, imbalance)

↓

**Step 7**
Preprocess: imputation, encoding, scaling, train/test split

↓

**Step 8**
Train and evaluate the Logistic Regression risk model

↓

**Step 9**
Derive Risk, Collection Priority, Cross-Sell, and Health scores

↓

**Step 10**
Save scores back to PostgreSQL

↓

**Step 11**
Connect Power BI live to the database

↓

**Step 12**
Build the 4-page dashboard

---

## 📊 Dashboard Features

- Executive KPI strip — portfolio size, exposure, at-risk count, average health score
- Risk score distribution and behavioral trend breakdown by segment
- Top risk-driving features, straight from model coefficients
- Collection priority queue ranked by risk × exposure
- DPD bucket breakdown
- Cross-sell eligible segment view

---

## 📈 Future Improvements

- XGBoost as a comparison model with SHAP-based explainability
- Streamlit live-scoring demo for single-customer what-if analysis
- Cross-validation in place of a single train/test split
- Probability calibration (Platt scaling / isotonic regression)
- Automated data refresh pipeline
- CI checks for SQL/notebook execution

---

## 👩‍💻 Author

**Supriya Patil**

Data Analytics | SQL | Python | Power BI | Credit Risk Modelling

---

## 📄 License

This project is intended for educational and portfolio purposes.

# Data Leakage Prevention

## The general rule

For a risk model, every feature used to predict an outcome must be derivable from information available **strictly before** the prediction point. If `TARGET` (default) is determined at loan application time, no feature may use data from *after* that application.

## Why this dataset is structurally leakage-resistant, by construction

Unlike a rolling time-series problem (where you must manually pick a cutoff date and exclude anything after it), the Home Credit dataset encodes time **relative to each customer's own application**, not on a shared calendar:

- `DAYS_BIRTH`, `DAYS_EMPLOYED`, `DAYS_ID_PUBLISH`, etc. in `application_train` are negative day-counts *before* the application date.
- `DAYS_INSTALMENT`, `DAYS_ENTRY_PAYMENT` in `installments_payments` are likewise relative to the application.
- `MONTHS_BALANCE` in `credit_card_balance` and `POS_CASH_balance` is a negative month-count relative to the application (0 = month of application, -1 = one month before, etc.).

Every raw source table used in `customer_features` (and its Spark equivalent, `customer_features_spark`) only contains history **up to and including** the application. There is no column anywhere in these tables that encodes information from *after* the application date — the dataset simply doesn't carry it. This means the trend features (`lateness_trend`, `utilization_trend`, `dpd_trend`) are safe by construction: "recent 6 months" and "prior 6 months" both refer to months before the application, never after.

## Where a real risk still exists (and how it's handled)

1. **`target` itself must never appear as an input feature.** Verified explicitly: `src/models/train.py` and `notebooks/03_modelling.ipynb` both build `X` via `df_encoded.drop(columns=['sk_id_curr', 'target'])` — `target` is dropped before any feature matrix is built, not filtered out silently later.
2. **Test-set information must not leak into preprocessing.** `RobustScaler` and the imputation medians are fit *only* on `X_train`, then applied (not re-fit) to `X_test` — see Phase 8's documented rule: "fit only on train, transform both." The same pattern is used in `src/models/train.py`.
3. **The Spark and SQL pipelines must derive from the same raw sources, not from each other's output.** `customer_features_spark` is built directly from the `raw_*` staging tables, exactly like the SQL pipeline — not from `customer_features` itself — so there's no risk of one pipeline's engineered (and potentially already-biased) output silently becoming an input to the other.

## What this dataset genuinely cannot demonstrate

A real production system also needs to guard against **cross-customer temporal leakage** — e.g., accidentally training on a portfolio-wide statistic computed using future customers' data (a common real leakage source: "average default rate this month" computed after the fact and joined back in). This static, single-snapshot Kaggle dataset has no ongoing portfolio timeline to demonstrate that failure mode against, so it isn't exercised here. Documented as a known scope limitation, not implemented — see the README's Limitations section.

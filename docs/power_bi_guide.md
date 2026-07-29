# Power BI Dashboard — Build Guide

Data sources in Postgres (`customer360` database):
- `vw_customer_dashboard` — one row per customer, all demographics + behavioral features + scores
- `feature_importance` — model coefficients, for the "top risk drivers" chart

## 1. Connect

1. Open Power BI Desktop.
2. **Get Data** → **More...** → search **PostgreSQL database** → Connect.
3. Server: `localhost:5432`. Database: `customer360`.
4. Data Connectivity mode: **Import** (307K rows is small enough for Import, and it makes every visual much faster/more interactive than DirectQuery).
5. In the Navigator, tick both `vw_customer_dashboard` and `feature_importance` → **Load**.
6. Enter your Postgres username/password when prompted (same as your `.env` credentials).

## 2. Quick data check (Power Query, optional but recommended)

Home → Transform Data. Confirm:
- `risk_segment`, `health_segment`, `cross_sell_eligible`, `code_gender`, etc. are **Text**
- `risk_score`, `collection_priority_score`, `health_score`, `amt_credit`, `income` are **Decimal Number**
- `target`, `collection_rank` are **Whole Number**

Close & Apply when done.

## 3. DAX measures to create

Right-click `vw_customer_dashboard` in the Fields pane → **New Measure**, for each of these:

```dax
Total Portfolio = COUNTROWS(vw_customer_dashboard)

Total Loan Exposure = SUM(vw_customer_dashboard[amt_credit])

Customers at Risk = CALCULATE(COUNTROWS(vw_customer_dashboard), vw_customer_dashboard[risk_segment] = "High Risk")

Avg Health Score = AVERAGE(vw_customer_dashboard[health_score])

Early Warning Count = CALCULATE(
    COUNTROWS(vw_customer_dashboard),
    FILTER(
        vw_customer_dashboard,
        vw_customer_dashboard[lateness_trend] > 0 || vw_customer_dashboard[utilization_trend] > 0 || vw_customer_dashboard[dpd_trend] > 0
    )
)

Cross-Sell Opportunities = CALCULATE(COUNTROWS(vw_customer_dashboard), vw_customer_dashboard[cross_sell_eligible] = "Eligible")

Actual Default Rate = DIVIDE(SUM(vw_customer_dashboard[target]), COUNTROWS(vw_customer_dashboard))
```

**Why `Early Warning Count` is its own measure, not the same as `Customers at Risk`:** `risk_segment` is a static snapshot of current risk. Early Warning should mean "this customer's behavior is *actively worsening right now*" — customers whose lateness, utilization, or DPD trend is positive (getting worse), regardless of their current absolute risk level. That's a genuinely different, more forward-looking cut of the portfolio — exactly the distinction the whole project is built around.

## 4. Color coding — set up once, reuse everywhere

Select the `health_segment` column → **Column tools** → **Data category**... actually simpler: for each visual that uses `health_segment`, manually set:
- 🟢 Healthy → green (`#2E7D32` or similar)
- 🟡 Monitor → amber (`#F9A825`)
- 🔴 High Risk → red (`#C62828`)

Do this once on the first visual, then use **Format → Copy formatting** or just repeat manually — Power BI doesn't have a single global "always color this category this color" setting outside of a theme file, so consistency takes a little manual repetition across visuals.

## 5. Page 1 — Executive Overview

- **6 Card visuals** across the top: `Total Portfolio`, `Total Loan Exposure`, `Customers at Risk`, `Avg Health Score`, `Early Warning Count`, `Cross-Sell Opportunities`
- **Donut chart**: Legend = `health_segment`, Values = `Total Portfolio` (or count of rows) — color per the scheme above
- **Donut or bar chart**: Legend = `risk_segment`, Values = count
- **Column chart**: Axis = `risk_segment`, Values = `Actual Default Rate` — this is a great "proof the model works" visual; the bars should climb clearly from Low → Medium → High Risk

## 6. Page 2 — Risk & Early Warning

- **Histogram**: Axis = `risk_score` (binned — right-click the field → New group, bin size ~10), Values = count. Shows the score distribution.
- **Line/area or column chart**: compare average `lateness_trend`, `utilization_trend`, `dpd_trend` across `risk_segment` — put all three trend measures on one chart, `risk_segment` on the axis, to visually show trends worsening as risk climbs.
- **Horizontal bar chart** (this is the standout visual): switch data source to `feature_importance`. Axis = `feature`, Values = `abs_coefficient`, filter to `rank <= 15`, color by `direction` (Increases Risk = red, Decreases Risk = green). This is a genuine "why does the model think this" chart, straight from your actual trained coefficients — a great talking point in an interview.

## 7. Page 3 — Collection Priority Queue

- **Table visual**: sorted by `collection_rank` ascending, columns: `sk_id_curr`, `risk_score`, `amt_credit`, `collection_priority_score`, `avg_dpd_overall`, `max_dpd_ever`. Filter to top 50-100 rows (Visual level filter → `collection_rank` ≤ 100) — this is literally the actionable "call these customers first" list.
- **DPD bucket bar chart**: create a calculated column first — Modeling tab → New Column:
  ```dax
  DPD Bucket = SWITCH(
      TRUE(),
      vw_customer_dashboard[avg_dpd_overall] = 0, "0 (Current)",
      vw_customer_dashboard[avg_dpd_overall] <= 30, "1-30",
      vw_customer_dashboard[avg_dpd_overall] <= 60, "31-60",
      vw_customer_dashboard[avg_dpd_overall] <= 90, "61-90",
      "90+"
  )
  ```
  Then a column chart: Axis = `DPD Bucket`, Values = count.
- **KPI Card**: `Total Loan Exposure` filtered to `risk_segment = High Risk` (add a visual-level filter) — "money at risk right now."

## 8. Page 4 — Cross-Sell Opportunities

- **Card**: `Cross-Sell Opportunities` count, and a second card with `%` (new measure: `Cross-Sell % = DIVIDE([Cross-Sell Opportunities], [Total Portfolio])`)
- **Bar chart**: Axis = `occupation_type` or `name_education_type`, Values = count, filtered to `cross_sell_eligible = "Eligible"` — shows which segments are producing the most safe, high-value candidates.
- **Table**: top candidates — filter to `cross_sell_eligible = "Eligible"`, sort by `income` descending, show `sk_id_curr`, `income`, `amt_credit`, `risk_score`.

## 9. Save

**File → Save As** → save into your project's `dashboard/` folder as `customer360.pbix`.

---

Since I can't click through the actual interface, work through this at your own pace and paste me anything that errors or looks off (a DAX formula not working, a visual not rendering right) — I can debug those from the text/formula alone, same as we did with the notebooks.

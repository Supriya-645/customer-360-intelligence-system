# Entity-Relationship Diagram — Customer 360 Intelligence System

All in-scope tables join back to `application_train` via `SK_ID_CURR`.
`bureau` also carries `SK_ID_BUREAU`, which is the only thing `bureau_balance`
can join on — since `bureau_balance` cannot be linked to an individual
customer without adding that extra hop, it is excluded from `customer_features`
(shown below, dashed, for completeness).

```mermaid
erDiagram
    APPLICATION_TRAIN ||--o{ INSTALLMENTS_PAYMENTS : "SK_ID_CURR"
    APPLICATION_TRAIN ||--o{ CREDIT_CARD_BALANCE : "SK_ID_CURR"
    APPLICATION_TRAIN ||--o{ POS_CASH_BALANCE : "SK_ID_CURR"
    APPLICATION_TRAIN ||--o{ BUREAU : "SK_ID_CURR"
    BUREAU ||--o{ BUREAU_BALANCE : "SK_ID_BUREAU (excluded from features)"

    APPLICATION_TRAIN {
        int SK_ID_CURR PK
        int TARGET
        float AMT_INCOME_TOTAL
        float AMT_CREDIT
        string NAME_CONTRACT_TYPE
        int DAYS_BIRTH
        int DAYS_EMPLOYED
        float EXT_SOURCE_1
        float EXT_SOURCE_2
        float EXT_SOURCE_3
    }
    INSTALLMENTS_PAYMENTS {
        int SK_ID_CURR FK
        int SK_ID_PREV
        int DAYS_INSTALMENT
        int DAYS_ENTRY_PAYMENT
        float AMT_INSTALMENT
        float AMT_PAYMENT
    }
    CREDIT_CARD_BALANCE {
        int SK_ID_CURR FK
        int SK_ID_PREV
        int MONTHS_BALANCE
        float AMT_BALANCE
        float AMT_CREDIT_LIMIT_ACTUAL
        int SK_DPD
    }
    POS_CASH_BALANCE {
        int SK_ID_CURR FK
        int SK_ID_PREV
        int MONTHS_BALANCE
        int CNT_INSTALMENT
        int CNT_INSTALMENT_FUTURE
        int SK_DPD
    }
    BUREAU {
        int SK_ID_CURR FK
        int SK_ID_BUREAU PK
        string CREDIT_ACTIVE
        string CREDIT_TYPE
        int DAYS_CREDIT
        float AMT_CREDIT_SUM
        float AMT_CREDIT_SUM_DEBT
    }
    BUREAU_BALANCE {
        int SK_ID_BUREAU FK
        int MONTHS_BALANCE
        string STATUS
    }
```

## Join summary

| Table | Grain | Joins to `application_train` via | Used in `customer_features`? |
|---|---|---|---|
| `application_train` | 1 row per customer | — (base table) | Yes |
| `installments_payments` | 1 row per installment | `SK_ID_CURR` | Yes |
| `credit_card_balance` | 1 row per card per month | `SK_ID_CURR` | Yes |
| `POS_CASH_balance` | 1 row per loan per month | `SK_ID_CURR` | Yes |
| `bureau` | 1 row per external credit account | `SK_ID_CURR` | Yes |
| `bureau_balance` | 1 row per external account per month | `SK_ID_BUREAU` (no direct path to `SK_ID_CURR`) | **No** — excluded, see note above |

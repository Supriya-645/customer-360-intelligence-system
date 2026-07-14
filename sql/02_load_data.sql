-- Bulk-load raw CSVs into the staging tables created by 01_schema.sql
-- \copy is a psql client-side command: it streams the file from your machine
-- to the server, so it works without needing special server-side file permissions.

\copy raw_application_train FROM 'data/raw/HC_application_train.csv' WITH (FORMAT csv, HEADER true)
\copy raw_installments_payments FROM 'data/raw/HC_installments_payments.csv' WITH (FORMAT csv, HEADER true)
\copy raw_credit_card_balance FROM 'data/raw/HC_credit_card_balance.csv' WITH (FORMAT csv, HEADER true)
\copy raw_pos_cash_balance FROM 'data/raw/HC_POS_CASH_balance.csv' WITH (FORMAT csv, HEADER true)
\copy raw_bureau FROM 'data/raw/HC_bureau.csv' WITH (FORMAT csv, HEADER true)

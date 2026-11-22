CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.google_account` AS
SELECT
    'google' AS platform,
    JSON_VALUE(payload, '$.customer_id') AS account_id,
    JSON_VALUE(payload, '$.name') AS account_name
FROM `{{PROJECT_ID}}.bronze.google_customer_raw`;
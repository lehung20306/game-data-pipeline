CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_account` AS
SELECT
    'meta' AS platform,
    JSON_VALUE(payload, '$.account_id') AS account_id,
    JSON_VALUE(payload, '$.name') AS account_name
FROM `{{PROJECT_ID}}.bronze.meta_account_raw`;
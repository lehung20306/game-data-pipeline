CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_account` AS
WITH normalized AS (
    SELECT
        'meta' AS platform,
        JSON_VALUE(payload, '$.account_id') AS account_id,
        JSON_VALUE(payload, '$.name') AS account_name,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.meta_account_raw`
)
SELECT platform, account_id, account_name
FROM normalized
WHERE account_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id
    ORDER BY extracted_at DESC
) = 1;
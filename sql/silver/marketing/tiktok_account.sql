CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.tiktok_account` AS
SELECT
    'tiktok' AS platform,
    JSON_VALUE(payload, '$.advertiser_id') AS account_id,
    JSON_VALUE(payload, '$.advertiser_name') AS account_name
FROM `{{PROJECT_ID}}.bronze.tiktok_advertiser_raw`;
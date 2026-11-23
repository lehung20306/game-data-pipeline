CREATE OR REPLACE TABLE `{{PROJECT_ID}}.gold.dim_ad_account` AS
SELECT
    platform,
    account_id,
    account_name
FROM `{{PROJECT_ID}}.silver.meta_account`

UNION ALL BY NAME

SELECT
    platform,
    account_id,
    account_name
FROM `{{PROJECT_ID}}.silver.tiktok_account`

UNION ALL BY NAME

SELECT
    platform,
    account_id,
    account_name
FROM `{{PROJECT_ID}}.silver.google_account`;

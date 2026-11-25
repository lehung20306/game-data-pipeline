CREATE OR REPLACE TABLE `{{PROJECT_ID}}.gold.dim_ad` AS
SELECT
    platform,
    account_id,
    ad_id,
    ad_name,
    creative_format
FROM `{{PROJECT_ID}}.silver.meta_ad`

UNION ALL BY NAME

SELECT
    platform,
    account_id,
    ad_id,
    ad_name,
    creative_format
FROM `{{PROJECT_ID}}.silver.tiktok_ad`

UNION ALL BY NAME

SELECT
    platform,
    account_id,
    ad_id,
    ad_name,
    creative_format
FROM `{{PROJECT_ID}}.silver.google_ad`;

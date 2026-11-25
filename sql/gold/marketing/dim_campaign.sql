CREATE OR REPLACE TABLE `{{PROJECT_ID}}.gold.dim_campaign` AS
SELECT
    platform,
    account_id,
    campaign_id,
    campaign_name
FROM `{{PROJECT_ID}}.silver.meta_campaign`

UNION ALL BY NAME

SELECT
    platform,
    account_id,
    campaign_id,
    campaign_name
FROM `{{PROJECT_ID}}.silver.tiktok_campaign`

UNION ALL BY NAME

SELECT
    platform,
    account_id,
    campaign_id,
    campaign_name
FROM `{{PROJECT_ID}}.silver.google_campaign`;

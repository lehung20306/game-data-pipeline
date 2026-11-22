CREATE OR REPLACE TABLE `{{PROJECT_ID}}.gold.fact_ad_performance_daily`
PARTITION BY report_date AS
SELECT
    platform,
    account_id,
    campaign_id,
    ad_group_id,
    ad_id,
    report_date,
    country_code,
    spend_usd,
    impressions,
    clicks,
    installs,
    purchases,
    revenue_usd,
    extracted_at
FROM `{{PROJECT_ID}}.silver.meta_ad_performance_daily`

UNION ALL BY NAME

SELECT
    platform,
    account_id,
    campaign_id,
    ad_group_id,
    ad_id,
    report_date,
    country_code,
    spend_usd,
    impressions,
    clicks,
    installs,
    purchases,
    revenue_usd,
    extracted_at
FROM `{{PROJECT_ID}}.silver.tiktok_ad_performance_daily`

UNION ALL BY NAME

SELECT
    platform,
    account_id,
    campaign_id,
    ad_group_id,
    ad_id,
    report_date,
    country_code,
    spend_usd,
    impressions,
    clicks,
    installs,
    purchases,
    revenue_usd,
    extracted_at
FROM `{{PROJECT_ID}}.silver.google_ad_performance_daily`;

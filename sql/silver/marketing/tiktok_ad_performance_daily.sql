CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.tiktok_ad_performance_daily` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.metrics.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.metrics.adgroup_id') AS ad_group_id,
        JSON_VALUE(payload, '$.dimensions.ad_id') AS ad_id,
        SAFE.PARSE_DATE(
            '%Y-%m-%d',
            SUBSTR(JSON_VALUE(payload, '$.dimensions.stat_time_day'), 1, 10)
        ) AS report_date,
        UPPER(JSON_VALUE(payload, '$.dimensions.country_code')) AS country_code,
        SAFE_CAST(
            JSON_VALUE(payload, '$.metrics.spend') AS NUMERIC
        ) AS spend_usd,
        SAFE_CAST(
            JSON_VALUE(payload, '$.metrics.impressions') AS INT64
        ) AS impressions,
        SAFE_CAST(
            JSON_VALUE(payload, '$.metrics.clicks') AS INT64
        ) AS clicks,
        SAFE_CAST(
            JSON_VALUE(payload, '$.metrics.conversion') AS INT64
        ) AS installs,
        SAFE_CAST(
            JSON_VALUE(payload, '$.metrics.purchase') AS INT64
        ) AS purchases,
        SAFE_CAST(
            JSON_VALUE(payload, '$.metrics.total_purchase_value') AS NUMERIC
        ) AS revenue_usd,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.tiktok_reporting_raw`
)
SELECT *
FROM normalized
WHERE ad_id IS NOT NULL
    AND report_date IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_id, report_date, country_code
    ORDER BY extracted_at DESC
) = 1;

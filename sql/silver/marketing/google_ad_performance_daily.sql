CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.google_ad_performance_daily` AS
WITH geo_targets AS (
    SELECT
        JSON_VALUE(payload, '$.geoTargetConstant.resourceName') AS resource_name,
        UPPER(JSON_VALUE(payload, '$.geoTargetConstant.countryCode')) AS country_code,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.google_geo_target_raw`
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY JSON_VALUE(payload, '$.geoTargetConstant.resourceName')
        ORDER BY extracted_at DESC
    ) = 1
),
normalized AS (
    SELECT
        raw.source AS platform,
        raw.source_account_id AS account_id,
        JSON_VALUE(raw.payload, '$.campaign.id') AS campaign_id,
        JSON_VALUE(raw.payload, '$.adGroup.id') AS ad_group_id,
        JSON_VALUE(raw.payload, '$.adGroupAd.ad.id') AS ad_id,
        SAFE_CAST(
            JSON_VALUE(raw.payload, '$.segments.date') AS DATE
        ) AS report_date,
        geo.country_code,
        SAFE_CAST(
            JSON_VALUE(raw.payload, '$.metrics.costMicros') AS NUMERIC
        ) / 1000000 AS spend_usd,
        SAFE_CAST(
            JSON_VALUE(raw.payload, '$.metrics.impressions') AS INT64
        ) AS impressions,
        SAFE_CAST(
            JSON_VALUE(raw.payload, '$.metrics.clicks') AS INT64
        ) AS clicks,
        SAFE_CAST(
            SAFE_CAST(
                JSON_VALUE(raw.payload, '$.metrics.conversions') AS NUMERIC
            ) AS INT64
        ) AS installs,
        SAFE_CAST(
            GREATEST(
                SAFE_CAST(
                    JSON_VALUE(raw.payload, '$.metrics.allConversions') AS NUMERIC
                ) - SAFE_CAST(
                    JSON_VALUE(raw.payload, '$.metrics.conversions') AS NUMERIC
                ),
                0
            ) AS INT64
        ) AS purchases,
        SAFE_CAST(
            JSON_VALUE(raw.payload, '$.metrics.conversionsValue') AS NUMERIC
        ) AS revenue_usd,
        raw.extracted_at
    FROM `{{PROJECT_ID}}.bronze.google_reporting_raw` AS raw
    LEFT JOIN geo_targets AS geo
        ON geo.resource_name = JSON_VALUE(
            raw.payload, '$.segments.geoTargetCountry'
        )
)
SELECT *
FROM normalized
WHERE ad_id IS NOT NULL
    AND report_date IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_id, report_date, country_code
    ORDER BY extracted_at DESC
) = 1;

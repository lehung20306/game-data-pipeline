-- Rebuild all available history for Silver-only or when bootstrapping the table.
DECLARE full_refresh BOOL DEFAULT @since IS NULL OR NOT EXISTS (
    SELECT 1
    FROM `{{PROJECT_ID}}.silver.INFORMATION_SCHEMA.TABLES`
    WHERE table_name = 'google_ad_performance_daily'
);

-- Staging keeps the latest Bronze snapshot for each reporting key.
CREATE TEMP TABLE stg_google_ad_performance_daily AS
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
    AND (full_refresh OR report_date BETWEEN @since AND @until)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY platform, account_id, ad_id, report_date, country_code
    ORDER BY extracted_at DESC
) = 1;

IF full_refresh THEN
    CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.google_ad_performance_daily` AS
    SELECT * FROM stg_google_ad_performance_daily;
ELSE
    MERGE `{{PROJECT_ID}}.silver.google_ad_performance_daily` AS t
    USING stg_google_ad_performance_daily AS s
        ON t.platform = s.platform
        AND t.account_id IS NOT DISTINCT FROM s.account_id
        AND t.ad_id = s.ad_id
        AND t.report_date = s.report_date
        AND t.country_code IS NOT DISTINCT FROM s.country_code
    WHEN MATCHED AND s.extracted_at IS NOT NULL
        AND (t.extracted_at IS NULL OR s.extracted_at > t.extracted_at) THEN
        UPDATE SET
            campaign_id = s.campaign_id,
            ad_group_id = s.ad_group_id,
            spend_usd = s.spend_usd,
            impressions = s.impressions,
            clicks = s.clicks,
            installs = s.installs,
            purchases = s.purchases,
            revenue_usd = s.revenue_usd,
            extracted_at = s.extracted_at
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (
            platform, account_id, campaign_id, ad_group_id, ad_id,
            report_date, country_code, spend_usd, impressions, clicks,
            installs, purchases, revenue_usd, extracted_at
        )
        VALUES (
            s.platform, s.account_id, s.campaign_id, s.ad_group_id, s.ad_id,
            s.report_date, s.country_code, s.spend_usd, s.impressions, s.clicks,
            s.installs, s.purchases, s.revenue_usd, s.extracted_at
        );
END IF;

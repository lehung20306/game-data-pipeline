-- Rebuild all available history for Silver-only or when bootstrapping the table.
DECLARE full_refresh BOOL DEFAULT @since IS NULL OR NOT EXISTS (
    SELECT 1
    FROM `{{PROJECT_ID}}.silver.INFORMATION_SCHEMA.TABLES`
    WHERE table_name = 'tiktok_ad_performance_daily'
);

-- Staging keeps the latest Bronze snapshot for each reporting key.
CREATE TEMP TABLE stg_tiktok_ad_performance_daily AS
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
    AND (full_refresh OR report_date BETWEEN @since AND @until)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY platform, account_id, ad_id, report_date, country_code
    ORDER BY extracted_at DESC
) = 1;

IF full_refresh THEN
    CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.tiktok_ad_performance_daily` AS
    SELECT * FROM stg_tiktok_ad_performance_daily;
ELSE
    MERGE `{{PROJECT_ID}}.silver.tiktok_ad_performance_daily` AS t
    USING stg_tiktok_ad_performance_daily AS s
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

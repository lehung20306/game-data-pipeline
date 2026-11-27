-- Rebuild all available history for Silver-only or when bootstrapping the table.
DECLARE full_refresh BOOL DEFAULT @since IS NULL OR NOT EXISTS (
    SELECT 1
    FROM `{{PROJECT_ID}}.silver.INFORMATION_SCHEMA.TABLES`
    WHERE table_name = 'meta_ad_performance_daily'
);

-- Staging keeps the latest Bronze snapshot for each reporting key.
CREATE TEMP TABLE stg_meta_ad_performance_daily AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.adset_id') AS ad_group_id,
        JSON_VALUE(payload, '$.ad_id') AS ad_id,
        SAFE_CAST(
            JSON_VALUE(payload, '$.date_start')
            AS DATE
        ) AS report_date,
        UPPER(JSON_VALUE(payload, '$.country')) AS country_code,
        SAFE_CAST(
            JSON_VALUE(payload, '$.spend')
            AS NUMERIC
        ) AS spend_usd,
        SAFE_CAST(
            JSON_VALUE(payload, '$.impressions')
            AS INT64
        ) AS impressions,
        SAFE_CAST(
            JSON_VALUE(payload, '$.clicks')
            AS INT64
        ) AS clicks,
        COALESCE(
            (
                SELECT SUM(
                    SAFE_CAST(
                        JSON_VALUE(action, '$.value')
                        AS INT64
                    )
                )
                FROM UNNEST(
                    JSON_QUERY_ARRAY(payload, '$.actions')
                ) AS action
                WHERE JSON_VALUE(action, '$.action_type')
                    = 'mobile_app_install'
            ),
            0
        ) AS installs,
        COALESCE(
            (
                SELECT SUM(
                    SAFE_CAST(
                        JSON_VALUE(action, '$.value')
                        AS INT64
                    )
                )
                FROM UNNEST(
                    JSON_QUERY_ARRAY(payload, '$.actions')
                ) AS action
                WHERE JSON_VALUE(action, '$.action_type')
                    = 'app_custom_event.fb_mobile_purchase'
            ),
            0
        ) AS purchases,
        COALESCE(
            (
                SELECT SUM(
                    SAFE_CAST(
                        JSON_VALUE(action_value, '$.value')
                        AS NUMERIC
                    )
                )
                FROM UNNEST(
                    JSON_QUERY_ARRAY(payload, '$.action_values')
                ) AS action_value
                WHERE JSON_VALUE(action_value, '$.action_type')
                    = 'app_custom_event.fb_mobile_purchase'
            ),
            0
        ) AS revenue_usd,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.meta_insight_raw`
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
    CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_ad_performance_daily` AS
    SELECT * FROM stg_meta_ad_performance_daily;
ELSE
    MERGE `{{PROJECT_ID}}.silver.meta_ad_performance_daily` AS t
    USING stg_meta_ad_performance_daily AS s
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

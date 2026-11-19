CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_insights` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.adset_id') AS adset_id,
        JSON_VALUE(payload, '$.ad_id') AS ad_id,
        SAFE_CAST(
            JSON_VALUE(payload, '$.date_start')
            AS DATE
        ) AS report_date,
        JSON_VALUE(payload, '$.country') AS country,
        SAFE_CAST(
            JSON_VALUE(payload, '$.spend')
            AS NUMERIC
        ) AS spend,
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
        ) AS revenue,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.meta_insights_raw`
)
SELECT *
FROM normalized
WHERE ad_id IS NOT NULL
    AND report_date IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_id, report_date, country
    ORDER BY extracted_at DESC
) = 1;
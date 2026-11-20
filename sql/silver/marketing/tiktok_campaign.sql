CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.tiktok_campaign` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.campaign_name') AS campaign_name,
        JSON_VALUE(payload, '$.operation_status') AS source_configured_status,
        JSON_VALUE(payload, '$.secondary_status') AS source_effective_status,
        CASE JSON_VALUE(payload, '$.operation_status')
            WHEN 'ENABLE' THEN 'ENABLED'
            WHEN 'DISABLE' THEN 'DISABLED'
            ELSE 'UNKNOWN'
        END AS configured_status,
        CASE JSON_VALUE(payload, '$.secondary_status')
            WHEN 'CAMPAIGN_STATUS_ENABLE' THEN 'RUNNING'
            WHEN 'CAMPAIGN_STATUS_DISABLE' THEN 'PAUSED'
            WHEN 'CAMPAIGN_STATUS_TIME_DONE' THEN 'ENDED'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        JSON_VALUE(payload, '$.budget_mode') AS budget_mode,
        CASE
            WHEN JSON_VALUE(payload, '$.budget_mode') = 'BUDGET_MODE_DAY'
                THEN SAFE_CAST(JSON_VALUE(payload, '$.budget') AS NUMERIC)
        END AS daily_budget_usd,
        CAST(NULL AS TIMESTAMP) AS start_time,
        CAST(NULL AS TIMESTAMP) AS end_time,
        SAFE.PARSE_TIMESTAMP(
            '%Y-%m-%d %H:%M:%S',
            JSON_VALUE(payload, '$.create_time'),
            'UTC'
        ) AS created_at,
        SAFE.PARSE_TIMESTAMP(
            '%Y-%m-%d %H:%M:%S',
            JSON_VALUE(payload, '$.modify_time'),
            'UTC'
        ) AS updated_at,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.tiktok_campaign_raw`
)
SELECT *
FROM normalized
WHERE campaign_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, campaign_id
    ORDER BY extracted_at DESC
) = 1;

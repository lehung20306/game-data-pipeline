CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_campaign` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.id') AS campaign_id,
        JSON_VALUE(payload, '$.name') AS campaign_name,
        JSON_VALUE(payload, '$.status') AS source_configured_status,
        JSON_VALUE(payload, '$.effective_status') AS source_effective_status,
        CASE JSON_VALUE(payload, '$.status')
            WHEN 'ACTIVE' THEN 'ENABLED'
            WHEN 'PAUSED' THEN 'DISABLED'
            WHEN 'ARCHIVED' THEN 'ARCHIVED'
            ELSE 'UNKNOWN'
        END AS configured_status,
        CASE JSON_VALUE(payload, '$.effective_status')
            WHEN 'ACTIVE' THEN 'RUNNING'
            WHEN 'PAUSED' THEN 'PAUSED'
            WHEN 'ARCHIVED' THEN 'ARCHIVED'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        JSON_VALUE(payload, '$.bid_strategy') AS bid_strategy,
        SAFE_CAST(
            JSON_VALUE(payload, '$.daily_budget') AS NUMERIC
        ) / 100 AS daily_budget_usd,

        SAFE_CAST(
            JSON_VALUE(payload, '$.start_time') AS TIMESTAMP
        ) AS start_time,

        SAFE_CAST(
            JSON_VALUE(payload, '$.stop_time') AS TIMESTAMP
        ) AS end_time,
        extracted_at

    FROM `{{PROJECT_ID}}.bronze.meta_campaign_raw`
)
SELECT *
FROM normalized
WHERE campaign_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, campaign_id
    ORDER BY extracted_at DESC
) = 1;

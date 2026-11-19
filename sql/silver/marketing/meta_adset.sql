CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_adset` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.id') AS adset_id,
        JSON_VALUE(payload, '$.name') AS adset_name,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.effective_status') AS adset_status,
        JSON_VALUE(payload, '$.optimization_goal') AS optimization_goal,
        STRUCT(
            JSON_VALUE(
                payload,
                '$.promoted_object.application_id'
            ) AS application_id,
            JSON_VALUE(
                payload,
                '$.promoted_object.custom_event_type'
            ) AS custom_event_type,
            JSON_VALUE(
                payload,
                '$.promoted_object.object_store_url'
            ) AS object_store_url
        ) AS promoted_object,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.meta_adset_raw`
)
SELECT *
FROM normalized
WHERE adset_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, adset_id
    ORDER BY extracted_at DESC
) = 1;

CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_ad` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.id') AS ad_id,
        JSON_VALUE(payload, '$.name') AS ad_name,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.adset_id') AS ad_group_id,
        JSON_VALUE(payload, '$.status') AS source_configured_status,
        JSON_VALUE(payload, '$.effective_status') AS source_effective_status,
        CASE JSON_VALUE(payload, '$.status')
            WHEN 'ACTIVE' THEN 'ENABLED'
            WHEN 'PAUSED' THEN 'DISABLED'
            ELSE 'UNKNOWN'
        END AS configured_status,
        CASE JSON_VALUE(payload, '$.effective_status')
            WHEN 'ACTIVE' THEN 'RUNNING'
            WHEN 'PAUSED' THEN 'PAUSED'
            WHEN 'CAMPAIGN_PAUSED' THEN 'PAUSED'
            WHEN 'ARCHIVED' THEN 'ARCHIVED'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        JSON_VALUE(payload, '$.creative.id') AS creative_id,
        JSON_VALUE(payload, '$.creative.name') AS creative_name,
        JSON_VALUE(payload, '$.creative.object_type') AS creative_type,
        CASE
            WHEN JSON_VALUE(
                payload, '$.creative.asset_feed_spec.playable_asset_id'
            ) IS NOT NULL
                OR STARTS_WITH(UPPER(JSON_VALUE(payload, '$.name')), 'PLAY_')
                THEN 'PLAYABLE'
            WHEN JSON_VALUE(payload, '$.creative.object_type') = 'PHOTO'
                THEN 'IMAGE'
            WHEN JSON_VALUE(payload, '$.creative.object_type') = 'VIDEO'
                THEN 'VIDEO'
            ELSE 'UNKNOWN'
        END AS creative_format,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.meta_ad_raw`
)
SELECT *
FROM normalized
WHERE ad_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_id
    ORDER BY extracted_at DESC
) = 1;

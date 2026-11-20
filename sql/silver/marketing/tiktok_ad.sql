CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.tiktok_ad` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.ad_id') AS ad_id,
        JSON_VALUE(payload, '$.ad_name') AS ad_name,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.adgroup_id') AS ad_group_id,
        JSON_VALUE(payload, '$.operation_status') AS source_configured_status,
        JSON_VALUE(payload, '$.secondary_status') AS source_effective_status,
        CASE JSON_VALUE(payload, '$.operation_status')
            WHEN 'ENABLE' THEN 'ENABLED'
            WHEN 'DISABLE' THEN 'DISABLED'
            ELSE 'UNKNOWN'
        END AS configured_status,
        CASE JSON_VALUE(payload, '$.secondary_status')
            WHEN 'AD_STATUS_DELIVERY_OK' THEN 'RUNNING'
            WHEN 'AD_STATUS_DISABLE' THEN 'PAUSED'
            WHEN 'AD_STATUS_CAMPAIGN_DISABLE' THEN 'PAUSED'
            WHEN 'AD_STATUS_CAMPAIGN_TIME_DONE' THEN 'ENDED'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        JSON_VALUE(payload, '$.ad_format') AS creative_type,
        CASE
            WHEN NULLIF(JSON_VALUE(payload, '$.playable_url'), '') IS NOT NULL
                OR STARTS_WITH(UPPER(JSON_VALUE(payload, '$.ad_name')), 'PLAY_')
                THEN 'PLAYABLE'
            WHEN JSON_VALUE(payload, '$.ad_format') = 'SINGLE_IMAGE'
                THEN 'IMAGE'
            WHEN JSON_VALUE(payload, '$.ad_format') = 'SINGLE_VIDEO'
                THEN 'VIDEO'
            ELSE 'UNKNOWN'
        END AS creative_format,
        JSON_VALUE(payload, '$.video_id') AS video_id,
        JSON_VALUE_ARRAY(payload, '$.image_ids') AS image_ids,
        JSON_VALUE(payload, '$.playable_url') AS playable_url,
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
    FROM `{{PROJECT_ID}}.bronze.tiktok_ad_raw`
)
SELECT *
FROM normalized
WHERE ad_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_id
    ORDER BY extracted_at DESC
) = 1;

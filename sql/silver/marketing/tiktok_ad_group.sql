CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.tiktok_ad_group` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.adgroup_id') AS ad_group_id,
        JSON_VALUE(payload, '$.adgroup_name') AS ad_group_name,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.operation_status') AS source_configured_status,
        JSON_VALUE(payload, '$.secondary_status') AS source_effective_status,
        CASE JSON_VALUE(payload, '$.operation_status')
            WHEN 'ENABLE' THEN 'ENABLED'
            WHEN 'DISABLE' THEN 'DISABLED'
            ELSE 'UNKNOWN'
        END AS configured_status,
        CASE JSON_VALUE(payload, '$.secondary_status')
            WHEN 'ADGROUP_STATUS_DELIVERY_OK' THEN 'RUNNING'
            WHEN 'ADGROUP_STATUS_CAMPAIGN_DISABLE' THEN 'PAUSED'
            WHEN 'ADGROUP_STATUS_TIME_DONE' THEN 'ENDED'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        JSON_VALUE(payload, '$.optimization_goal') AS optimization_goal,
        JSON_VALUE(payload, '$.app_id') AS platform_app_id,
        JSON_VALUE(payload, '$.app_download_url') AS store_url,
        CASE JSON_VALUE(payload, '$.app_type')
            WHEN 'APP_ANDROID' THEN 'ANDROID'
            WHEN 'APP_IOS' THEN 'IOS'
        END AS app_os,
        JSON_VALUE_ARRAY(payload, '$.location_ids') AS target_location_ids,
        CAST(NULL AS ARRAY<STRING>) AS target_countries,
        JSON_VALUE_ARRAY(payload, '$.age_groups') AS target_age_groups,
        CAST(NULL AS INT64) AS target_age_min,
        CAST(NULL AS INT64) AS target_age_max,
        JSON_VALUE(payload, '$.gender') AS target_gender,
        JSON_VALUE_ARRAY(
            payload, '$.operating_systems'
        ) AS target_operating_systems,
        JSON_VALUE(payload, '$.audience_type') AS audience_type,
        SAFE.PARSE_TIMESTAMP(
            '%Y-%m-%d %H:%M:%S',
            JSON_VALUE(payload, '$.schedule_start_time'),
            'UTC'
        ) AS start_time,
        SAFE.PARSE_TIMESTAMP(
            '%Y-%m-%d %H:%M:%S',
            JSON_VALUE(payload, '$.schedule_end_time'),
            'UTC'
        ) AS end_time,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.tiktok_adgroup_raw`
)
SELECT *
FROM normalized
WHERE ad_group_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_group_id
    ORDER BY extracted_at DESC
) = 1;

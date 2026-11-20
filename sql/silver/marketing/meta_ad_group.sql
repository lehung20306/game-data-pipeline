CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_ad_group` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.id') AS ad_group_id,
        JSON_VALUE(payload, '$.name') AS ad_group_name,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
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
            WHEN 'CAMPAIGN_PAUSED' THEN 'PAUSED'
            WHEN 'ARCHIVED' THEN 'ARCHIVED'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        CASE JSON_VALUE(payload, '$.optimization_goal')
            WHEN 'APP_INSTALLS' THEN 'INSTALL'
            WHEN 'VALUE' THEN 'VALUE'
        END AS optimization_goal,
        JSON_VALUE(
            payload, '$.promoted_object.application_id'
        ) AS platform_app_id,
        JSON_VALUE(
            payload, '$.promoted_object.object_store_url'
        ) AS store_url,
        JSON_VALUE_ARRAY(
            payload, '$.targeting.geo_locations.countries'
        ) AS target_countries,
        SAFE_CAST(
            JSON_VALUE(payload, '$.targeting.age_min') AS INT64
        ) AS target_age_min,
        SAFE_CAST(
            JSON_VALUE(payload, '$.targeting.age_max') AS INT64
        ) AS target_age_max,
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
WHERE ad_group_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_group_id
    ORDER BY extracted_at DESC
) = 1;

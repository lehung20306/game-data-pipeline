CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.google_ad_group` AS
WITH normalized AS (
    SELECT
        raw.source AS platform,
        raw.source_account_id AS account_id,
        JSON_VALUE(raw.payload, '$.adGroup.id') AS ad_group_id,
        JSON_VALUE(raw.payload, '$.adGroup.name') AS ad_group_name,
        JSON_VALUE(raw.payload, '$.campaign.id') AS campaign_id,
        JSON_VALUE(raw.payload, '$.adGroup.status') AS source_configured_status,
        CAST(NULL AS STRING) AS source_effective_status,
        CASE JSON_VALUE(raw.payload, '$.adGroup.status')
            WHEN 'ENABLED' THEN 'ENABLED'
            WHEN 'PAUSED' THEN 'DISABLED'
            ELSE 'UNKNOWN'
        END AS configured_status,
        CASE
            WHEN campaign.delivery_status = 'ENDED' THEN 'ENDED'
            WHEN campaign.delivery_status = 'PAUSED' THEN 'PAUSED'
            WHEN JSON_VALUE(raw.payload, '$.adGroup.status') = 'PAUSED'
                THEN 'PAUSED'
            WHEN campaign.delivery_status = 'RUNNING'
                AND JSON_VALUE(raw.payload, '$.adGroup.status') = 'ENABLED'
                THEN 'RUNNING'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        campaign.optimization_goal,
        campaign.platform_app_id,
        CAST(NULL AS STRING) AS store_url,
        CAST(NULL AS ARRAY<STRING>) AS target_countries,
        CAST(NULL AS INT64) AS target_age_min,
        CAST(NULL AS INT64) AS target_age_max,
        JSON_VALUE(raw.payload, '$.adGroup.type') AS ad_group_type,
        raw.extracted_at
    FROM `{{PROJECT_ID}}.bronze.google_adgroup_raw` AS raw
    LEFT JOIN `{{PROJECT_ID}}.silver.google_campaign` AS campaign
        ON campaign.account_id = raw.source_account_id
        AND campaign.campaign_id = JSON_VALUE(raw.payload, '$.campaign.id')
)
SELECT *
FROM normalized
WHERE ad_group_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_group_id
    ORDER BY extracted_at DESC
) = 1;

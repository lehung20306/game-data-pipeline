CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.google_ad` AS
WITH normalized AS (
    SELECT
        raw.source AS platform,
        raw.source_account_id AS account_id,
        JSON_VALUE(raw.payload, '$.adGroupAd.ad.id') AS ad_id,
        JSON_VALUE(raw.payload, '$.adGroupAd.ad.name') AS ad_name,
        JSON_VALUE(raw.payload, '$.campaign.id') AS campaign_id,
        JSON_VALUE(raw.payload, '$.adGroup.id') AS ad_group_id,
        JSON_VALUE(raw.payload, '$.adGroupAd.status') AS source_configured_status,
        CAST(NULL AS STRING) AS source_effective_status,
        CASE JSON_VALUE(raw.payload, '$.adGroupAd.status')
            WHEN 'ENABLED' THEN 'ENABLED'
            WHEN 'PAUSED' THEN 'DISABLED'
            ELSE 'UNKNOWN'
        END AS configured_status,
        CASE
            WHEN campaign.delivery_status = 'ENDED' THEN 'ENDED'
            WHEN campaign.delivery_status = 'PAUSED' THEN 'PAUSED'
            WHEN ad_group.delivery_status = 'PAUSED' THEN 'PAUSED'
            WHEN JSON_VALUE(raw.payload, '$.adGroupAd.status') = 'PAUSED'
                THEN 'PAUSED'
            WHEN campaign.delivery_status = 'RUNNING'
                AND ad_group.delivery_status = 'RUNNING'
                AND JSON_VALUE(raw.payload, '$.adGroupAd.status') = 'ENABLED'
                THEN 'RUNNING'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        JSON_VALUE(raw.payload, '$.adGroupAd.ad.type') AS creative_type,
        CASE
            WHEN STARTS_WITH(
                UPPER(JSON_VALUE(raw.payload, '$.adGroupAd.ad.name')),
                'PLAY_'
            ) OR STARTS_WITH(
                UPPER(JSON_VALUE(raw.payload, '$.adGroupAd.ad.name')),
                'PLY_'
            ) THEN 'PLAYABLE'
            WHEN JSON_VALUE(raw.payload, '$.adGroupAd.ad.type') = 'IMAGE_AD'
                THEN 'IMAGE'
            WHEN JSON_VALUE(raw.payload, '$.adGroupAd.ad.type') = 'VIDEO_RESPONSIVE_AD'
                THEN 'VIDEO'
            ELSE 'UNKNOWN'
        END AS creative_format,
        JSON_VALUE_ARRAY(raw.payload, '$.adGroupAd.ad.finalUrls') AS final_urls,
        JSON_VALUE(raw.payload, '$.adGroupAd.ad.finalUrls[0]') AS store_url,
        raw.extracted_at
    FROM `{{PROJECT_ID}}.bronze.google_ad_raw` AS raw
    LEFT JOIN `{{PROJECT_ID}}.silver.google_campaign` AS campaign
        ON campaign.account_id = raw.source_account_id
        AND campaign.campaign_id = JSON_VALUE(raw.payload, '$.campaign.id')
    LEFT JOIN `{{PROJECT_ID}}.silver.google_ad_group` AS ad_group
        ON ad_group.account_id = raw.source_account_id
        AND ad_group.ad_group_id = JSON_VALUE(raw.payload, '$.adGroup.id')
)
SELECT *
FROM normalized
WHERE ad_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, ad_id
    ORDER BY extracted_at DESC
) = 1;

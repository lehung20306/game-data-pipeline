CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.google_campaign` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.campaign.id') AS campaign_id,
        JSON_VALUE(payload, '$.campaign.name') AS campaign_name,
        JSON_VALUE(payload, '$.campaign.status') AS source_configured_status,
        JSON_VALUE(payload, '$.campaign.servingStatus') AS source_effective_status,
        CASE JSON_VALUE(payload, '$.campaign.status')
            WHEN 'ENABLED' THEN 'ENABLED'
            WHEN 'PAUSED' THEN 'DISABLED'
            ELSE 'UNKNOWN'
        END AS configured_status,
        CASE
            WHEN JSON_VALUE(payload, '$.campaign.servingStatus') = 'ENDED'
                THEN 'ENDED'
            WHEN JSON_VALUE(payload, '$.campaign.status') = 'PAUSED'
                THEN 'PAUSED'
            WHEN JSON_VALUE(payload, '$.campaign.servingStatus') = 'SERVING'
                THEN 'RUNNING'
            ELSE 'UNKNOWN'
        END AS delivery_status,
        JSON_VALUE(payload, '$.campaign.advertisingChannelType') AS advertising_channel_type,
        JSON_VALUE(payload, '$.campaign.appCampaignSetting.appId') AS platform_app_id,
        JSON_VALUE(payload, '$.campaign.appCampaignSetting.appStore') AS app_store,
        CASE
            WHEN JSON_VALUE(
                payload, '$.campaign.appCampaignSetting.biddingStrategyGoalType'
            ) = 'OPTIMIZE_INSTALLS_TARGET_INSTALL_COST'
                OR JSON_VALUE(payload, '$.campaign.biddingStrategyType') = 'TARGET_CPA'
                THEN 'INSTALL'
            WHEN JSON_VALUE(
                payload, '$.campaign.appCampaignSetting.biddingStrategyGoalType'
            ) = 'OPTIMIZE_RETURN_ON_ADVERTISING_SPEND'
                OR JSON_VALUE(payload, '$.campaign.biddingStrategyType') = 'MAXIMIZE_CONVERSION_VALUE'
                THEN 'VALUE'
        END AS optimization_goal,
        JSON_VALUE(payload, '$.campaign.biddingStrategyType') AS bid_strategy,
        SAFE_CAST(
            JSON_VALUE(payload, '$.campaignBudget.amountMicros') AS NUMERIC
        ) / 1000000 AS daily_budget_usd,
        TIMESTAMP(
            SAFE_CAST(JSON_VALUE(payload, '$.campaign.startDate') AS DATE),
            'UTC'
        ) AS start_time,
        CASE
            WHEN JSON_VALUE(payload, '$.campaign.endDate') = '2037-12-30'
                THEN CAST(NULL AS TIMESTAMP)
            ELSE TIMESTAMP(
                SAFE_CAST(JSON_VALUE(payload, '$.campaign.endDate') AS DATE),
                'UTC'
            )
        END AS end_time,
        extracted_at
    FROM `{{PROJECT_ID}}.bronze.google_campaign_raw`
)
SELECT *
FROM normalized
WHERE campaign_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id, campaign_id
    ORDER BY extracted_at DESC
) = 1;

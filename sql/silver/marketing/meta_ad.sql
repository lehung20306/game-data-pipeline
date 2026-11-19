CREATE OR REPLACE TABLE `{{PROJECT_ID}}.silver.meta_ad` AS
WITH normalized AS (
    SELECT
        source AS platform,
        source_account_id AS account_id,
        JSON_VALUE(payload, '$.id') AS ad_id,
        JSON_VALUE(payload, '$.name') AS ad_name,
        JSON_VALUE(payload, '$.campaign_id') AS campaign_id,
        JSON_VALUE(payload, '$.adset_id') AS adset_id,
        JSON_VALUE(payload, '$.effective_status') AS ad_status,
        JSON_VALUE(payload, '$.creative.id') AS creative_id,
        JSON_VALUE(payload, '$.creative.name') AS creative_name,
        JSON_VALUE(payload, '$.creative.object_type') AS creative_type,
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

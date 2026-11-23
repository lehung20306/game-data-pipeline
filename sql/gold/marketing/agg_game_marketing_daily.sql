CREATE OR REPLACE TABLE `{{PROJECT_ID}}.gold.agg_game_marketing_daily` AS
SELECT
    fapd.report_date,
    fapd.platform,
    daa.account_name,
    SAFE_DIVIDE(SUM(fapd.clicks), SUM(fapd.impressions))*100 AS CTR,
    SAFE_DIVIDE(SUM(fapd.spend_usd), SUM(fapd.impressions))*1000 AS CPM,
    SAFE_DIVIDE(SUM(fapd.spend_usd), SUM(fapd.clicks)) AS CPC,
    SAFE_DIVIDE(SUM(fapd.spend_usd), SUM(fapd.installs)) AS CPI,
    SAFE_DIVIDE(SUM(fapd.spend_usd), SUM(fapd.purchases)) AS CPA,
    SAFE_DIVIDE(SUM(fapd.revenue_usd), SUM(fapd.spend_usd)) AS ROAS,
FROM `{{PROJECT_ID}}.gold.fact_ad_performance_daily` fapd
LEFT JOIN `{{PROJECT_ID}}.gold.dim_ad_account` daa
    ON daa.platform = fapd.platform 
    AND daa.account_id = fapd.account_id
GROUP BY fapd.report_date,
    fapd.platform,
    daa.account_name

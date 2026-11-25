CREATE OR REPLACE TABLE `{{PROJECT_ID}}.gold.agg_game_country_daily` AS
WITH daily_totals AS (
    SELECT
        fapd.report_date,
        fapd.platform,
        daa.account_name,
        fapd.country_code,
        SUM(fapd.spend_usd) AS spend_usd,
        SUM(fapd.impressions) AS impressions,
        SUM(fapd.clicks) AS clicks,
        SUM(fapd.installs) AS installs,
        SUM(fapd.purchases) AS purchases,
        SUM(fapd.revenue_usd) AS revenue_usd
    FROM `{{PROJECT_ID}}.gold.fact_ad_performance_daily` AS fapd
    LEFT JOIN `{{PROJECT_ID}}.gold.dim_ad_account` AS daa
        ON daa.platform = fapd.platform
        AND daa.account_id = fapd.account_id
    GROUP BY
        fapd.report_date,
        fapd.platform,
        daa.account_name,
        fapd.country_code
)
SELECT
    report_date,
    platform,
    account_name,
    country_code,
    spend_usd,
    impressions,
    clicks,
    installs,
    purchases,
    revenue_usd,
    SAFE_DIVIDE(clicks, impressions) * 100 AS CTR,
    SAFE_DIVIDE(spend_usd, impressions) * 1000 AS CPM,
    SAFE_DIVIDE(spend_usd, clicks) AS CPC,
    SAFE_DIVIDE(spend_usd, installs) AS CPI,
    SAFE_DIVIDE(spend_usd, purchases) AS CPA,
    SAFE_DIVIDE(revenue_usd, spend_usd) AS ROAS
FROM daily_totals;

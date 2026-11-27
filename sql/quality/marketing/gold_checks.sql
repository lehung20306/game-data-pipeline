-- A healthy run returns no rows.
WITH expected_days AS (
    SELECT report_date, platform
    FROM UNNEST(GENERATE_DATE_ARRAY(@since, @until)) AS report_date
    CROSS JOIN UNNEST(['meta', 'tiktok', 'google']) AS platform
),
fact_totals AS (
    SELECT report_date, platform, SUM(spend_usd) AS spend_usd, SUM(installs) AS installs, SUM(revenue_usd) AS revenue_usd
    FROM `{{PROJECT_ID}}.gold.fact_ad_performance_daily`
    WHERE report_date BETWEEN @since AND @until
    GROUP BY report_date, platform
),
aggregate_rows AS (
    SELECT 'agg_game_country_daily' AS table_name, report_date, platform, spend_usd, installs, revenue_usd
    FROM `{{PROJECT_ID}}.gold.agg_game_country_daily`
    WHERE report_date BETWEEN @since AND @until

    UNION ALL

    SELECT 'agg_campaign_marketing_daily', report_date, platform, spend_usd, installs, revenue_usd
    FROM `{{PROJECT_ID}}.gold.agg_campaign_marketing_daily`
    WHERE report_date BETWEEN @since AND @until

    UNION ALL

    SELECT 'agg_creative_format_daily', report_date, platform, spend_usd, installs, revenue_usd
    FROM `{{PROJECT_ID}}.gold.agg_creative_format_daily`
    WHERE report_date BETWEEN @since AND @until
),
aggregate_totals AS (
    SELECT table_name, report_date, platform, SUM(spend_usd) AS spend_usd, SUM(installs) AS installs, SUM(revenue_usd) AS revenue_usd
    FROM aggregate_rows
    GROUP BY table_name, report_date, platform
),
expected_totals AS (
    SELECT table_name, report_date, platform, spend_usd, installs, revenue_usd
    FROM fact_totals
    CROSS JOIN UNNEST([
        'agg_game_country_daily',
        'agg_campaign_marketing_daily',
        'agg_creative_format_daily'
    ]) AS table_name
),
duplicate_fact_keys AS (
    SELECT
        platform,
        account_id,
        ad_id,
        report_date,
        country_code,
        COUNT(*) AS row_count
    FROM `{{PROJECT_ID}}.gold.fact_ad_performance_daily`
    WHERE report_date BETWEEN @since AND @until
    GROUP BY
        platform,
        account_id,
        ad_id,
        report_date,
        country_code
    HAVING row_count > 1
)

SELECT
    'missing_fact_day' AS check_name,
    report_date,
    platform,
    CAST(NULL AS STRING) AS account_id,
    CAST(NULL AS STRING) AS ad_id,
    CAST(NULL AS STRING) AS country_code,
    'fact_ad_performance_daily' AS table_name,
    CAST(NULL AS INT64) AS row_count,
    CAST(NULL AS NUMERIC) AS expected_spend_usd,
    CAST(NULL AS NUMERIC) AS actual_spend_usd,
    CAST(NULL AS INT64) AS expected_installs,
    CAST(NULL AS INT64) AS actual_installs,
    CAST(NULL AS NUMERIC) AS expected_revenue_usd,
    CAST(NULL AS NUMERIC) AS actual_revenue_usd
FROM expected_days
LEFT JOIN fact_totals AS fact USING (report_date, platform)
WHERE fact.report_date IS NULL

UNION ALL

SELECT
    CASE
        WHEN expected.table_name IS NULL THEN 'unexpected_aggregate_group'
        WHEN actual.table_name IS NULL THEN 'missing_aggregate_group'
        ELSE 'metric_mismatch'
    END AS check_name,
    report_date,
    platform,
    CAST(NULL AS STRING) AS account_id,
    CAST(NULL AS STRING) AS ad_id,
    CAST(NULL AS STRING) AS country_code,
    table_name,
    CAST(NULL AS INT64) AS row_count,
    expected.spend_usd AS expected_spend_usd,
    actual.spend_usd AS actual_spend_usd,
    expected.installs AS expected_installs,
    actual.installs AS actual_installs,
    expected.revenue_usd AS expected_revenue_usd,
    actual.revenue_usd AS actual_revenue_usd
FROM expected_totals AS expected
FULL OUTER JOIN aggregate_totals AS actual USING (table_name, report_date, platform)
WHERE expected.table_name IS NULL
    OR actual.table_name IS NULL
    OR expected.spend_usd IS DISTINCT FROM actual.spend_usd
    OR expected.installs IS DISTINCT FROM actual.installs
    OR expected.revenue_usd IS DISTINCT FROM actual.revenue_usd

UNION ALL

SELECT
    'duplicate_fact_key' AS check_name,
    report_date,
    platform,
    account_id,
    ad_id,
    country_code,
    'fact_ad_performance_daily' AS table_name,
    row_count,
    CAST(NULL AS NUMERIC) AS expected_spend_usd,
    CAST(NULL AS NUMERIC) AS actual_spend_usd,
    CAST(NULL AS INT64) AS expected_installs,
    CAST(NULL AS INT64) AS actual_installs,
    CAST(NULL AS NUMERIC) AS expected_revenue_usd,
    CAST(NULL AS NUMERIC) AS actual_revenue_usd
FROM duplicate_fact_keys
ORDER BY report_date, platform, table_name, check_name;

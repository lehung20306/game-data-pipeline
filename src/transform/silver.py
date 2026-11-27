import logging
from datetime import date

from google.cloud import bigquery

from src.pipeline_logging import error_context
from src.transform.sql_runner import run_sql_files

logger = logging.getLogger(__name__)

META_PERFORMANCE_QUERY = "marketing/meta_ad_performance_daily.sql"
TIKTOK_PERFORMANCE_QUERY = "marketing/tiktok_ad_performance_daily.sql"
GOOGLE_PERFORMANCE_QUERY = "marketing/google_ad_performance_daily.sql"
QUERY_FILES = [
    "marketing/meta_account.sql",
    "marketing/meta_campaign.sql",
    "marketing/meta_ad_group.sql",
    "marketing/meta_ad.sql",
    META_PERFORMANCE_QUERY,
    "marketing/tiktok_account.sql",
    "marketing/tiktok_campaign.sql",
    "marketing/tiktok_ad_group.sql",
    "marketing/tiktok_ad.sql",
    TIKTOK_PERFORMANCE_QUERY,
    "marketing/google_account.sql",
    "marketing/google_campaign.sql",
    "marketing/google_ad_group.sql",
    "marketing/google_ad.sql",
    GOOGLE_PERFORMANCE_QUERY,
]


def run_silver(since=None, until=None):
    if (since is None) != (until is None):
        raise ValueError("since and until must be provided together")
    if since is not None:
        since = date.fromisoformat(since)
        until = date.fromisoformat(until)
        if since > until:
            raise ValueError("since must be on or before until")

    date_parameters = [
        bigquery.ScalarQueryParameter("since", "DATE", since),
        bigquery.ScalarQueryParameter("until", "DATE", until),
    ]
    run_sql_files(
        "silver",
        QUERY_FILES,
        query_parameters={
            META_PERFORMANCE_QUERY: date_parameters,
            TIKTOK_PERFORMANCE_QUERY: date_parameters,
            GOOGLE_PERFORMANCE_QUERY: date_parameters,
        },
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    try:
        run_silver()
    except Exception as error:
        logger.error("Silver failed | %s", error_context(error))
        raise SystemExit(1) from None

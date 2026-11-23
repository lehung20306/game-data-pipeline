import logging

from src.pipeline_logging import error_context
from src.transform.sql_runner import run_sql_files

logger = logging.getLogger(__name__)

QUERY_FILES = [
    "marketing/meta_account.sql",
    "marketing/meta_campaign.sql",
    "marketing/meta_ad_group.sql",
    "marketing/meta_ad.sql",
    "marketing/meta_ad_performance_daily.sql",
    "marketing/tiktok_account.sql",
    "marketing/tiktok_campaign.sql",
    "marketing/tiktok_ad_group.sql",
    "marketing/tiktok_ad.sql",
    "marketing/tiktok_ad_performance_daily.sql",
    "marketing/google_account.sql",
    "marketing/google_campaign.sql",
    "marketing/google_ad_group.sql",
    "marketing/google_ad.sql",
    "marketing/google_ad_performance_daily.sql",
]

def run_silver():
    run_sql_files("silver", QUERY_FILES)


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

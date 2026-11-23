import logging

from src.pipeline_logging import error_context
from src.transform.sql_runner import run_sql_files

QUERY_FILES = [
    "marketing/dim_ad_account.sql",
    "marketing/fact_ad_performance_daily.sql",
    "marketing/agg_game_marketing_daily.sql",
]
logger = logging.getLogger(__name__)


def run_gold():
    run_sql_files("gold", QUERY_FILES)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        run_gold()
    except Exception as error:
        logger.error("Gold failed | %s", error_context(error))
        raise SystemExit(1) from None

import argparse
import logging
from datetime import date, datetime, timedelta, timezone

from src.load.bronze import run_google_pipeline, run_meta_pipeline, run_tiktok_pipeline
from src.transform.gold import run_gold
from src.transform.silver import run_silver
from src.pipeline_logging import error_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def run_all_pipelines(since, until):
    failed_sources = []
    for source, runner in (
        ("meta", run_meta_pipeline),
        ("tiktok", run_tiktok_pipeline),
        ("google", run_google_pipeline),
    ):
        try:
            runner(since, until)
        except Exception as error:
            logger.error("Bronze failed | platform=%s %s", source, error_context(error))
            failed_sources.append(source)
    if failed_sources:
        raise RuntimeError(f"Silver and Gold skipped: Bronze failed for {failed_sources}")

    run_silver(since=since, until=until)
    run_gold()
    logger.info("All Bronze, Silver and Gold pipelines completed successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Marketing data pipeline")
    parser.add_argument("--since", help="Report start date (YYYY-MM-DD)")
    parser.add_argument("--until", help="Report end date (YYYY-MM-DD)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--silver-only",
        action="store_true",
        help="Rebuild Silver from existing Bronze without calling APIs",
    )
    mode.add_argument(
        "--gold-only",
        action="store_true",
        help="Rebuild Gold from existing Silver tables",
    )
    args = parser.parse_args()

    try:
        if args.gold_only:
            run_gold()
        elif args.silver_only:
            run_silver()
        else:
            # Fetch the latest 3 complete UTC reporting days.
            until_date = datetime.now(timezone.utc).date() - timedelta(days=1)
            since_date = until_date - timedelta(days=2)
            since = args.since or since_date.isoformat()
            until = args.until or until_date.isoformat()
            if date.fromisoformat(since) > date.fromisoformat(until):
                parser.error("--since must be on or before --until")
            run_all_pipelines(since, until)
    except Exception as error:
        logger.error("Pipeline failed | %s", error_context(error))
        raise SystemExit(1) from None

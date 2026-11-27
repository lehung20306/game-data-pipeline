import argparse
from datetime import date
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

from src.pipeline_logging import error_context

BASE_DIR = Path(__file__).resolve().parents[2]
QUERY_FILE = BASE_DIR / "sql" / "quality" / "marketing" / "gold_checks.sql"
logger = logging.getLogger(__name__)


def run_marketing_quality(since, until):
    since_date = date.fromisoformat(since)
    until_date = date.fromisoformat(until)
    if since_date > until_date:
        raise ValueError("since must be on or before until")

    load_dotenv(BASE_DIR / ".env")
    project_id = os.environ["GCP_PROJECT_ID"]
    sql = QUERY_FILE.read_text(encoding="utf-8").replace("{{PROJECT_ID}}", project_id)
    config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("since", "DATE", since_date),
        bigquery.ScalarQueryParameter("until", "DATE", until_date),
    ])

    logger.info("Marketing quality started | since=%s until=%s", since, until)
    with bigquery.Client(project=project_id) as client:
        job = client.query(sql, job_config=config)
        results = job.result()
        for issue in results:
            details = (
                ("account_id", issue.account_id),
                ("ad_id", issue.ad_id),
                ("country_code", issue.country_code),
                ("row_count", issue.row_count),
                ("expected_spend_usd", issue.expected_spend_usd),
                ("actual_spend_usd", issue.actual_spend_usd),
                ("expected_installs", issue.expected_installs),
                ("actual_installs", issue.actual_installs),
                ("expected_revenue_usd", issue.expected_revenue_usd),
                ("actual_revenue_usd", issue.actual_revenue_usd),
            )
            detail_log = " ".join(
                f"{name}={value if value is not None else '-'}"
                for name, value in details
            )
            logger.error(
                "Marketing quality issue | check=%s date=%s platform=%s table=%s %s",
                issue.check_name, issue.report_date, issue.platform, issue.table_name,
                detail_log,
            )
        issue_count = results.total_rows
        logger.log(
            logging.ERROR if issue_count else logging.INFO,
            "Marketing quality completed | issues=%d job_id=%s", issue_count, job.job_id,
        )
    if issue_count:
        raise RuntimeError(f"Marketing quality found {issue_count} issues")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(description="Check Gold Marketing data quality")
    parser.add_argument("--since", required=True, help="First report date (YYYY-MM-DD)")
    parser.add_argument("--until", required=True, help="Last report date (YYYY-MM-DD)")
    args = parser.parse_args()
    try:
        run_marketing_quality(args.since, args.until)
    except Exception as error:
        logger.error("Marketing quality failed | %s", error_context(error))
        raise SystemExit(1) from None

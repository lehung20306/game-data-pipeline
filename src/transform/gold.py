import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

from src.pipeline_logging import error_context

BASE_DIR = Path(__file__).resolve().parents[2]
QUERY_FILE = BASE_DIR / "sql" / "gold" / "fact_ad_performance_daily.sql"
logger = logging.getLogger(__name__)


def run_gold():
    load_dotenv(BASE_DIR / ".env")
    project_id = os.environ["GCP_PROJECT_ID"]
    sql = QUERY_FILE.read_text(encoding="utf-8").replace("{{PROJECT_ID}}", project_id)
    client = bigquery.Client(project=project_id)

    logger.info("Gold transformation started | query=%s", QUERY_FILE.name)
    job = None
    try:
        job = client.query(sql)
        job.result()
    except Exception:
        logger.error(
            "Gold transformation did not complete | query=%s job_id=%s",
            QUERY_FILE.name, getattr(job, "job_id", None),
        )
        raise
    logger.info(
        "Gold transformation completed | query=%s job_id=%s",
        QUERY_FILE.name, job.job_id,
    )


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

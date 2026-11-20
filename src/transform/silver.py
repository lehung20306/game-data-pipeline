
    
  
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
logger = logging.getLogger(__name__)

META_SILVER_QUERIES = [
    "marketing/meta_campaign.sql",
    "marketing/meta_ad_group.sql",
    "marketing/meta_ad.sql",
    "marketing/meta_ad_performance_daily.sql",
]

TIKTOK_SILVER_QUERIES = [
    "marketing/tiktok_campaign.sql",
    "marketing/tiktok_ad_group.sql",
    "marketing/tiktok_ad.sql",
    "marketing/tiktok_ad_performance_daily.sql",
]

GOOGLE_SILVER_QUERIES = [
    "marketing/google_campaign.sql",
    "marketing/google_ad_group.sql",
    "marketing/google_ad.sql",
    "marketing/google_ad_performance_daily.sql",
]

ALL_SILVER_QUERIES = (
    META_SILVER_QUERIES
    + TIKTOK_SILVER_QUERIES
    + GOOGLE_SILVER_QUERIES
)

def run_silver(query_files):
    project_id = os.environ["GCP_PROJECT_ID"]
    client = bigquery.Client(project=project_id)
    sql_dir = BASE_DIR / "sql" / "silver"
    for query_file in query_files:
        sql_path = sql_dir / query_file
        logger.info("Starting Silver transformation: %s", query_file)
        # Read SQL template
        sql_template = sql_path.read_text(encoding="utf-8")
        # Replace environment variables in SQL
        sql = sql_template.replace(
            "{{PROJECT_ID}}",
            project_id
        )
        try:
            # Execute SQL in BigQuery
            job = client.query(sql)
            # Wait until the query finishes
            job.result()
            logger.info(
                "Silver transformation completed: %s | Job ID: %s",
                query_file,
                job.job_id
            )
        except Exception:
            logger.exception(
                "Silver transformation failed: %s",
                query_file
            )
            raise
    logger.info("All Silver transformations completed successfully")

def run_meta_silver():
    run_silver(META_SILVER_QUERIES)

def run_tiktok_silver():
    run_silver(TIKTOK_SILVER_QUERIES)

def run_google_silver():
    run_silver(GOOGLE_SILVER_QUERIES)

def run_all_silver():
    run_silver(ALL_SILVER_QUERIES)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    run_all_silver()


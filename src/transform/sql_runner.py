import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

from src.pipeline_logging import error_context

BASE_DIR = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


def run_sql_files(layer, query_files, *, query_parameters=None):
    load_dotenv(BASE_DIR / ".env")
    project_id = os.environ["GCP_PROJECT_ID"]
    sql_dir = BASE_DIR / "sql" / layer
    queries = []
    for query_file in query_files:
        try:
            template = (sql_dir / query_file).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            logger.error(
                "SQL read failed | layer=%s query=%s %s",
                layer, query_file, error_context(error),
            )
            raise
        queries.append((query_file, template.replace("{{PROJECT_ID}}", project_id)))

    client = bigquery.Client(project=project_id)
    for query_file, sql in queries:
        logger.info("Transformation started | layer=%s query=%s", layer, query_file)
        job = None
        try:
            parameters = (query_parameters or {}).get(query_file)
            if parameters is None:
                job = client.query(sql)
            else:
                job_config = bigquery.QueryJobConfig(query_parameters=parameters)
                job = client.query(sql, job_config=job_config)
            job.result()
        except Exception as error:
            logger.error(
                "Transformation failed | layer=%s query=%s job_id=%s %s",
                layer, query_file, getattr(job, "job_id", None), error_context(error),
            )
            raise
        logger.info(
            "Transformation completed | layer=%s query=%s job_id=%s",
            layer, query_file, job.job_id,
        )
    logger.info("Transformations completed | layer=%s queries=%d", layer, len(queries))

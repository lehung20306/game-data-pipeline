import os
import re
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from google.cloud import bigquery

from src.pipeline_logging import error_context

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
logger = logging.getLogger(__name__)

def load_to_bronze(table_name, rows, source, source_account_id=None, account_id_field=None, write_disposition="WRITE_APPEND"):
    account_scope = source_account_id if source_account_id is not None else "snapshot"
    if not rows:
        logger.info("Bronze load skipped | source=%s account_id=%s table=%s rows=0",
                    source, account_scope, table_name)
        return 0
    if not re.fullmatch(r"[a-z][a-z0-9_]*", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    project_id = os.environ["GCP_PROJECT_ID"]
    table_id = f"{project_id}.bronze.{table_name}"
    # Use Application Default Credentials.
    client = bigquery.Client(project=project_id)
    # Define a shared schema for all tables.
    schema = [
        bigquery.SchemaField("source", "STRING"),
        bigquery.SchemaField("source_account_id", "STRING"),
        bigquery.SchemaField("payload", "JSON"),
        bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    ]
    extracted_at = datetime.now(timezone.utc).isoformat()
    prepared_rows = []
    for row in rows:
        prepared_rows.append({
            "source": source,
            "source_account_id": str(
                row[account_id_field]
                if account_id_field
                else source_account_id
            ),
            "payload": row,
            "extracted_at": extracted_at,
        })
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=write_disposition,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )
    load_job = None
    try:
        load_job = client.load_table_from_json(prepared_rows, table_id, job_config=job_config)
        load_job.result()
    except Exception as error:
        logger.error(
            "Bronze load failed | source=%s account_id=%s table=%s job_id=%s %s",
            source, account_scope, table_name, getattr(load_job, "job_id", None), error_context(error),
        )
        raise
    logger.info(
        "Bronze load completed | source=%s account_id=%s table=%s rows=%d job_id=%s disposition=%s",
        source, account_scope, table_name, load_job.output_rows, load_job.job_id, write_disposition,
    )
    return load_job.output_rows

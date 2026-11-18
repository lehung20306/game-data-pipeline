import os
import re
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from google.cloud import bigquery

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
logger = logging.getLogger(__name__)

def load_to_bronze(table_name, rows, source, source_account_id=None):
    if not rows:
        logger.warning("No data to load into %s", table_name)
        return 0
    if not re.fullmatch(r"[a-z][a-z0-9_]*", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    project_id = os.environ["GCP_PROJECT_ID"]
    dataset_id = os.getenv("BQ_BRONZE_DATASET")
    table_id = f"{project_id}.{dataset_id}.{table_name}"
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
            "source_account_id": (
                str(source_account_id)
                if source_account_id is not None
                else None
            ),
            "payload": row,
            "extracted_at": extracted_at,
        })
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )
    logger.info(
        "Loading %d rows into %s",
        len(prepared_rows),
        table_id,
    )
    load_job = client.load_table_from_json(
        prepared_rows,
        table_id,
        job_config=job_config,
    )
    load_job.result()
    logger.info(
        "Successfully loaded %d rows into %s",
        load_job.output_rows,
        table_id,
    )
    return load_job.output_rows

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


def load_bronze_accounts(platform, accounts, account_id_field, fetch_datasets):
    failed_count = 0
    for account in accounts:
        account_id = account[account_id_field]
        logger.debug("Account started | platform=%s account_id=%s", platform, account_id)
        try:
            # Complete all extracts for this account before loading any of its datasets.
            datasets = list(fetch_datasets(account))
            for table_name, rows in datasets:
                load_to_bronze(
                    table_name,
                    rows,
                    source=platform,
                    source_account_id=account_id,
                )
        except Exception as error:
            logger.error(
                "Account failed | platform=%s account_id=%s %s",
                platform, account_id, error_context(error),
            )
            failed_count += 1
        else:
            logger.debug("Account completed | platform=%s account_id=%s", platform, account_id)

    logger.log(
        logging.ERROR if failed_count else logging.INFO,
        "Bronze finished | platform=%s succeeded=%d failed=%d",
        platform, len(accounts) - failed_count, failed_count,
    )
    if failed_count:
        raise RuntimeError(f"Bronze failed for {platform}")


def run_meta_pipeline(since, until):
    from src.extract.marketing.meta_api import (
        get_meta_accounts,
        get_meta_campaigns,
        get_meta_adsets,
        get_meta_ads,
        get_meta_insights,
    )

    accounts = get_meta_accounts()
    if not accounts:
        raise RuntimeError("No Meta accounts configured")
    logger.info(
        "Bronze started | platform=meta accounts=%d since=%s until=%s",
        len(accounts), since, until,
    )
    load_to_bronze(
        "meta_account_raw",
        accounts,
        source="meta",
        source_account_id=None,
        account_id_field="account_id",
        write_disposition="WRITE_TRUNCATE",
    )

    def fetch_datasets(account):
        api_id = account["id"]
        return [
            ("meta_campaign_raw", get_meta_campaigns(api_id)),
            ("meta_adset_raw", get_meta_adsets(api_id)),
            ("meta_ad_raw", get_meta_ads(api_id)),
            ("meta_insight_raw", get_meta_insights(api_id, since, until)),
        ]

    load_bronze_accounts("meta", accounts, "account_id", fetch_datasets)


def run_tiktok_pipeline(since, until):
    from src.extract.marketing.tiktok_api import (
        get_tiktok_advertisers,
        get_tiktok_campaigns,
        get_tiktok_adgroups,
        get_tiktok_ads,
        get_tiktok_reporting,
    )

    advertisers = get_tiktok_advertisers()
    if not advertisers:
        raise RuntimeError("No TikTok advertisers configured")
    logger.info(
        "Bronze started | platform=tiktok accounts=%d since=%s until=%s",
        len(advertisers), since, until,
    )
    load_to_bronze(
        "tiktok_advertiser_raw",
        advertisers,
        source="tiktok",
        source_account_id=None,
        account_id_field="advertiser_id",
        write_disposition="WRITE_TRUNCATE",
    )

    def fetch_datasets(advertiser):
        advertiser_id = advertiser["advertiser_id"]
        return [
            ("tiktok_campaign_raw", get_tiktok_campaigns(advertiser_id)),
            ("tiktok_adgroup_raw", get_tiktok_adgroups(advertiser_id)),
            ("tiktok_ad_raw", get_tiktok_ads(advertiser_id)),
            ("tiktok_reporting_raw", get_tiktok_reporting(advertiser_id, since, until)),
        ]

    load_bronze_accounts("tiktok", advertisers, "advertiser_id", fetch_datasets)


def run_google_pipeline(since, until):
    from src.extract.marketing.google_api import (
        get_google_customers,
        get_google_campaigns,
        get_google_adgroups,
        get_google_ads,
        get_google_reporting,
        get_google_geo_targets,
    )

    customers = get_google_customers()
    if not customers:
        raise RuntimeError("No Google Ads customers configured")
    logger.info(
        "Bronze started | platform=google accounts=%d since=%s until=%s",
        len(customers), since, until,
    )
    load_to_bronze(
        "google_customer_raw",
        customers,
        source="google",
        source_account_id=None,
        account_id_field="customer_id",
        write_disposition="WRITE_TRUNCATE",
    )
    # The geo-target lookup is shared across all Google Ads customers.
    geo_customer_id = customers[0]["customer_id"]
    geo_targets = get_google_geo_targets(geo_customer_id)
    if not geo_targets:
        raise RuntimeError("Google Ads geo-target lookup is empty")
    load_to_bronze(
        "google_geo_target_raw",
        geo_targets,
        source="google",
        source_account_id=geo_customer_id,
    )

    def fetch_datasets(customer):
        customer_id = customer["customer_id"]
        return [
            ("google_campaign_raw", get_google_campaigns(customer_id)),
            ("google_adgroup_raw", get_google_adgroups(customer_id)),
            ("google_ad_raw", get_google_ads(customer_id)),
            ("google_reporting_raw", get_google_reporting(customer_id, since, until)),
        ]

    load_bronze_accounts("google", customers, "customer_id", fetch_datasets)

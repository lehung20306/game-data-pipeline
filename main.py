import argparse
import logging
from datetime import date, datetime, timedelta, timezone
from src.extract.marketing.meta_api import (
    get_meta_accounts,
    get_meta_campaigns,
    get_meta_adsets,
    get_meta_ads,
    get_meta_insights,
)
from src.extract.marketing.tiktok_api import (
    get_tiktok_advertisers,
    get_tiktok_campaigns,
    get_tiktok_adgroups,
    get_tiktok_ads,
    get_tiktok_reporting,
)
from src.extract.marketing.google_api import (
    get_google_customers,
    get_google_campaigns,
    get_google_adgroups,
    get_google_ads,
    get_google_reporting,
    get_google_geo_targets,
)
from src.load.bronze_loader import load_to_bronze
from src.transform.silver import run_all_silver
from src.transform.silver import run_silver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

def run_meta_pipeline(since, until):
    accounts = get_meta_accounts()
    if not accounts:
        raise RuntimeError("No Meta accounts configured")
    load_to_bronze(
    "meta_account_raw",
        accounts,
        source="meta",
        source_account_id=None,
        account_id_field="account_id",
        write_disposition="WRITE_TRUNCATE"
    )
    logger.info("Starting Meta pipeline")
    logger.info("Total accounts: %d", len(accounts))
    logger.info("Date range: %s to %s", since, until)
    failed_accounts = []
    for account in accounts:
        account_id = account["account_id"]
        api_id = account["api_id"]
        game = account["game"]
        logger.info(
            "Processing account: %s | Game: %s",
            api_id,
            game,
        )
        try:
            datasets = [
                ("meta_campaign_raw", get_meta_campaigns(api_id)),
                ("meta_adset_raw", get_meta_adsets(api_id)),
                ("meta_ad_raw", get_meta_ads(api_id)),
                ("meta_insight_raw", get_meta_insights(api_id, since, until))
            ]
            for table_name, rows in datasets:
                load_to_bronze(
                    table_name,
                    rows,
                    source="meta",
                    source_account_id=account_id,
                )
            logger.info("Account %s completed successfully", api_id)
        except Exception:
            logger.exception(
                "Failed to process account %s",
                api_id,
            )
            failed_accounts.append(api_id)
    if failed_accounts:
        raise RuntimeError(
            f"Meta pipeline failed for accounts: {failed_accounts}"
        )
    logger.info("Meta pipeline completed successfully")

def run_tiktok_pipeline(since, until):
    advertisers = get_tiktok_advertisers()
    if not advertisers:
        raise RuntimeError("No TikTok advertisers configured")
    load_to_bronze(
        "tiktok_advertiser_raw",
        advertisers,
        source="tiktok",
        source_account_id=None,
        account_id_field="advertiser_id",
        write_disposition="WRITE_TRUNCATE"
    )
    logger.info("Starting TikTok pipeline | %d advertisers", len(advertisers))
    logger.info("Date range: %s to %s", since, until)
    failed_advertisers = []
    for advertiser in advertisers:
        advertiser_id = advertiser["advertiser_id"]
        logger.info(
            "Processing TikTok advertiser: %s | Game: %s",
            advertiser_id,
            advertiser["game"],
        )
        try:
            datasets = [
                ("tiktok_campaign_raw", get_tiktok_campaigns(advertiser_id)),
                ("tiktok_adgroup_raw", get_tiktok_adgroups(advertiser_id)),
                ("tiktok_ad_raw", get_tiktok_ads(advertiser_id)),
                ("tiktok_reporting_raw", get_tiktok_reporting(advertiser_id, since, until))
            ]
            for table_name, rows in datasets:
                load_to_bronze(
                    table_name,
                    rows,
                    source="tiktok",
                    source_account_id=advertiser_id,
                )
            logger.info("TikTok advertiser %s completed", advertiser_id)
        except Exception:
            logger.exception("Failed TikTok advertiser %s", advertiser_id)
            failed_advertisers.append(advertiser_id)

    if failed_advertisers:
        raise RuntimeError(
            f"TikTok pipeline failed for advertisers: {failed_advertisers}"
        )
    logger.info("TikTok pipeline completed successfully")

def run_google_pipeline(since, until):
    customers = get_google_customers()
    if not customers:
        raise RuntimeError("No Google Ads customers configured")
    load_to_bronze(
        "google_customer_raw",
        customers,
        source="google",
        source_account_id=None,
        account_id_field="customer_id",
        write_disposition="WRITE_TRUNCATE"
    )
    logger.info("Starting Google Ads pipeline | %d customers", len(customers))
    logger.info("Date range: %s to %s", since, until)
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
    failed_customers = []
    for customer in customers:
        customer_id = customer["customer_id"]
        logger.info(
            "Processing Google customer: %s | Game: %s",
            customer_id,
            customer["game"],
        )
        try:
            datasets = [
                ("google_campaign_raw", get_google_campaigns(customer_id)),
                ("google_adgroup_raw", get_google_adgroups(customer_id)),
                ("google_ad_raw", get_google_ads(customer_id)),
                ("google_reporting_raw", get_google_reporting(customer_id, since, until))
            ]
            for table_name, rows in datasets:
                load_to_bronze(
                    table_name,
                    rows,
                    source="google",
                    source_account_id=customer_id,
                )
            logger.info("Google customer %s completed", customer_id)
        except Exception:
            logger.exception("Failed Google customer %s", customer_id)
            failed_customers.append(customer_id)
    if failed_customers:
        raise RuntimeError(
            f"Google Ads pipeline failed for customers: {failed_customers}"
        )
    logger.info("Google Ads pipeline completed successfully")

def run_all_pipelines(since, until, silver_only=False):
    if not silver_only:
        failed_sources = []
        for source, runner in (
            ("meta", run_meta_pipeline),
            ("tiktok", run_tiktok_pipeline),
            ("google", run_google_pipeline)
        ):
            try:
                runner(since, until)
            except Exception:
                logger.exception("Bronze extraction failed for %s", source)
                failed_sources.append(source)
        if failed_sources:
            raise RuntimeError(
                f"Silver skipped: Bronze extraction failed for {failed_sources}"
            )
    logger.info("Starting Silver transformations for all platforms")
    run_all_silver()
    logger.info("All Bronze and Silver pipelines completed successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Marketing data pipeline")
    parser.add_argument("--since", help="Report start date (YYYY-MM-DD)")
    parser.add_argument("--until", help="Report end date (YYYY-MM-DD)")
    parser.add_argument(
        "--silver-only",
        action="store_true",
        help="Rebuild Silver from existing Bronze without calling APIs",
    )
    args = parser.parse_args()

    # Fetch the latest 3 complete UTC reporting days.
    until_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    since_date = until_date - timedelta(days=2)
    since = args.since or since_date.isoformat()
    until = args.until or until_date.isoformat()
    if date.fromisoformat(since) > date.fromisoformat(until):
        parser.error("--since must be on or before --until")

    run_all_pipelines(since, until, silver_only=args.silver_only)
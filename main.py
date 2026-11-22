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
from src.pipeline_logging import error_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

def run_meta_pipeline(since, until):
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
        write_disposition="WRITE_TRUNCATE"
    )
    failed_accounts = []
    for account in accounts:
        account_id = account["account_id"]
        api_id = account["id"]
        logger.debug("Account started | platform=meta account_id=%s", account_id)
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
            logger.debug("Account completed | platform=meta account_id=%s", account_id)
        except Exception as error:
            logger.error(
                "Account failed | platform=meta account_id=%s %s", account_id, error_context(error),
            )
            failed_accounts.append(account_id)
    logger.log(
        logging.ERROR if failed_accounts else logging.INFO,
        "Bronze finished | platform=meta succeeded=%d failed=%d",
        len(accounts) - len(failed_accounts), len(failed_accounts),
    )
    if failed_accounts:
        raise RuntimeError("Meta Bronze failed")

def run_tiktok_pipeline(since, until):
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
        write_disposition="WRITE_TRUNCATE"
    )
    failed_advertisers = []
    for advertiser in advertisers:
        advertiser_id = advertiser["advertiser_id"]
        logger.debug("Account started | platform=tiktok account_id=%s", advertiser_id)
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
            logger.debug("Account completed | platform=tiktok account_id=%s", advertiser_id)
        except Exception as error:
            logger.error(
                "Account failed | platform=tiktok account_id=%s %s", advertiser_id, error_context(error),
            )
            failed_advertisers.append(advertiser_id)
    logger.log(
        logging.ERROR if failed_advertisers else logging.INFO,
        "Bronze finished | platform=tiktok succeeded=%d failed=%d",
        len(advertisers) - len(failed_advertisers), len(failed_advertisers),
    )
    if failed_advertisers:
        raise RuntimeError("TikTok Bronze failed")

def run_google_pipeline(since, until):
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
        write_disposition="WRITE_TRUNCATE"
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
    failed_customers = []
    for customer in customers:
        customer_id = customer["customer_id"]
        logger.debug("Account started | platform=google account_id=%s", customer_id)
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
            logger.debug("Account completed | platform=google account_id=%s", customer_id)
        except Exception as error:
            logger.error(
                "Account failed | platform=google account_id=%s %s", customer_id, error_context(error),
            )
            failed_customers.append(customer_id)
    logger.log(
        logging.ERROR if failed_customers else logging.INFO,
        "Bronze finished | platform=google succeeded=%d failed=%d",
        len(customers) - len(failed_customers), len(failed_customers),
    )
    if failed_customers:
        raise RuntimeError("Google Ads Bronze failed")

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
            except Exception as error:
                logger.error("Bronze failed | platform=%s %s", source, error_context(error))
                failed_sources.append(source)
        if failed_sources:
            raise RuntimeError(
                f"Silver skipped: Bronze extraction failed for {failed_sources}"
            )
    logger.info("Silver started | mode=%s", "silver_only" if silver_only else "full")
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

    try:
        run_all_pipelines(since, until, silver_only=args.silver_only)
    except Exception as error:
        logger.error("Pipeline failed | %s", error_context(error))
        raise SystemExit(1) from None
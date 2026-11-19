import logging
from datetime import datetime, timedelta, timezone
from src.extract.marketing.meta_api import (
    get_meta_accounts,
    get_meta_campaigns,
    get_meta_adsets,
    get_meta_ads,
    get_meta_insights,
)
from src.load.bronze_loader import load_to_bronze

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

def run_meta_pipeline(since, until):
    accounts = get_meta_accounts()
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
            # Extract data from Meta API.
            campaigns = get_meta_campaigns(api_id)
            adsets = get_meta_adsets(api_id)
            ads = get_meta_ads(api_id)
            insights = get_meta_insights(api_id, since, until)
            logger.info(
                "Extracted: %d campaigns, %d adsets, %d ads, %d insights",
                len(campaigns),
                len(adsets),
                len(ads),
                len(insights),
            )
            # Load raw JSON records into BigQuery Bronze.
            load_to_bronze(
                "meta_campaign_raw",
                campaigns,
                source="meta",
                source_account_id=account_id,
            )
            load_to_bronze(
                "meta_adset_raw",
                adsets,
                source="meta",
                source_account_id=account_id,
            )
            load_to_bronze(
                "meta_ad_raw",
                ads,
                source="meta",
                source_account_id=account_id,
            )
            load_to_bronze(
                "meta_insights_raw",
                insights,
                source="meta",
                source_account_id=account_id,
            )
            logger.info(
                "Account %s completed successfully",
                api_id,
            )
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

if __name__ == "__main__":

    # Fetch the latest 3 complete UTC reporting days.
    until_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    since_date = until_date - timedelta(days=2)
    since = since_date.isoformat()
    until = until_date.isoformat()
    run_meta_pipeline(since, until)

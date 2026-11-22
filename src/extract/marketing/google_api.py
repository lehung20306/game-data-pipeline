import os
from datetime import date
import requests
import yaml
from pathlib import Path
from dotenv import load_dotenv
import logging

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")
GOOGLE_TOKEN= os.getenv("GOOGLE_ACCESS_TOKEN")
GOOGLE_DEVELOPER_TOKEN = os.getenv("GOOGLE_DEVELOPER_TOKEN")
GOOGLE_LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_LOGIN_CUSTOMER_ID")
GOOGLE_BASE = os.getenv("GOOGLE_BASE").rstrip("/")
logger = logging.getLogger(__name__)

def _google_headers():
    access_token = GOOGLE_TOKEN
    developer_token = GOOGLE_DEVELOPER_TOKEN
    login_customer_id = GOOGLE_LOGIN_CUSTOMER_ID
    return {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
        "login-customer-id": login_customer_id,
        "Content-Type": "application/json",
    }

def get_google_customers():
    url = f"{GOOGLE_BASE}/customers:listAccessibleCustomers"
    response = requests.get(
        url,
        headers=_google_headers(),
        timeout=60
    )
    response.raise_for_status()
    customer_ids = [
        name.split("/")[-1]
        for name in response.json()["resourceNames"]
    ]
    customers = []
    for customer_id in customer_ids:
        query = """
            SELECT
                customer.id,
                customer.descriptive_name
            FROM customer
        """
        rows = get_google_rows(customer_id, query)
        if not rows:
            raise RuntimeError(
                f"No customer information returned for {customer_id}"
            )
        customers.append({
            "customer_id": str(rows[0]["customer"]["id"]),
            "name": rows[0]["customer"]["descriptiveName"]
        })
    return customers

def google_post(customer_id, query):
    customer_id = str(customer_id).replace("-", "")
    if not (customer_id.isascii() and customer_id.isdigit()):
        raise ValueError(f"Invalid Google Ads customer ID: {customer_id}")
    url = f"{GOOGLE_BASE}/customers/{customer_id}/googleAds:searchStream"
    response = requests.post(
        url,
        headers=_google_headers(),
        json={"query": query},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()

def get_google_rows(customer_id, query):
    batches = google_post(customer_id, query)
    if isinstance(batches, dict):
        batches = [batches]
    if not isinstance(batches, list):
        raise ValueError("Unexpected Google searchStream response format")
    rows = []
    for batch in batches:
        if not isinstance(batch, dict):
            raise ValueError("Unexpected Google searchStream batch format")
        if "error" in batch:
            raise RuntimeError(f"Google Ads API error: {batch['error']}")
        rows.extend(batch.get("results", []))
    return rows

def get_google_campaigns(customer_id):
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.serving_status,
            campaign.advertising_channel_type,
            campaign.start_date,
            campaign.end_date,
            campaign.app_campaign_setting.app_id,
            campaign.app_campaign_setting.app_store,
            campaign.app_campaign_setting.bidding_strategy_goal_type,
            campaign.bidding_strategy_type,
            campaign_budget.amount_micros
        FROM campaign
    """
    return get_google_rows(customer_id, query)

def get_google_adgroups(customer_id):
    query = """
        SELECT
            ad_group.id,
            ad_group.name,
            ad_group.status,
            ad_group.type,
            campaign.id
        FROM ad_group
    """
    return get_google_rows(customer_id, query)

def get_google_ads(customer_id):
    query = """
        SELECT
            ad_group_ad.ad.id,
            ad_group_ad.ad.name,
            ad_group_ad.ad.type,
            ad_group_ad.ad.final_urls,
            ad_group_ad.status,
            ad_group.id,
            campaign.id
        FROM ad_group_ad
    """
    return get_google_rows(customer_id, query)

def get_google_reporting(customer_id, since, until):
    since_date = date.fromisoformat(since)
    until_date = date.fromisoformat(until)
    if since_date > until_date:
        raise ValueError("since must be on or before until")
    query = f"""
        SELECT
            segments.date,
            segments.geo_target_country,
            campaign.id,
            ad_group.id,
            ad_group_ad.ad.id,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.all_conversions,
            metrics.conversions_value
        FROM ad_group_ad
        WHERE segments.date BETWEEN '{since_date}' AND '{until_date}'
        ORDER BY segments.date, campaign.id, ad_group.id, ad_group_ad.ad.id
    """
    return get_google_rows(customer_id, query)

def get_google_geo_targets(customer_id):
    query = """
        SELECT
            geo_target_constant.id,
            geo_target_constant.country_code,
            geo_target_constant.resource_name
        FROM geo_target_constant
    """
    return get_google_rows(customer_id, query)
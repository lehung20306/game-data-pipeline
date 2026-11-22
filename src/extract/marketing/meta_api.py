import os
import time
import requests
import yaml
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")
META_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_BASE = os.getenv("META_BASE").rstrip("/")
logger = logging.getLogger(__name__)

def meta_get(url, params):
    while True:
        body = requests.get(url, params=params, timeout=60).json()
        if "error" not in body:
            return body                              
        if body["error"]["code"] == 17:                 
            logger.warning("Meta rate limit reached. Retrying in 60 seconds.")
            time.sleep(60)
            continue
        raise RuntimeError(f"Meta API error: {body['error']}")

def get_meta_pages(url, params):
    rows = []
    while url:
        body = meta_get(url, params)
        rows.extend(body.get("data", []))
        url = body.get("paging", {}).get("next")
        # The next URL already contains all query parameters.
        params = None
    return rows

def get_meta_accounts():
    url = f"{META_BASE}/me/adaccounts"
    params = {
        "access_token": META_TOKEN,
        "fields": "account_id,name,currency,timezone_name",
        "limit": 500,
    }
    accounts = get_meta_pages(url, params)

    return [
        {
            "account_id": str(account["account_id"]),
            "account_name": account.get("name"),
            "currency": account.get("currency"),
            "timezone": account.get("timezone_name"),
        }
        for account in accounts
    ]

def get_meta_accounts():
    url = f"{META_BASE}/me/adaccounts"
    params = {
        "access_token": META_TOKEN,
        "fields": "id,account_id,name",
        "limit": 500
    }
    return get_meta_pages(url, params)

def get_meta_campaigns(account_id):
    url = f"{META_BASE}/{account_id}/campaigns"
    params = {
        "access_token": META_TOKEN,
        "fields": (
            "id,name,status,effective_status,"
            "daily_budget,start_time,stop_time,bid_strategy"
        ),
        "limit": 500
    }
    return get_meta_pages(url, params)

def get_meta_adsets(account_id):
    url = f"{META_BASE}/{account_id}/adsets"
    params = {
        "access_token": META_TOKEN,
        "fields": (
            "id,name,campaign_id,status,effective_status,"
            "optimization_goal,targeting,promoted_object"
        ),
        "limit": 500
    }
    return get_meta_pages(url, params)

def get_meta_ads(account_id):
    url = f"{META_BASE}/{account_id}/ads"
    params = {
        "access_token": META_TOKEN,
        "fields": (
            "id,name,adset_id,campaign_id,status,"
            "effective_status,"
            "creative{id,name,object_type,asset_feed_spec}"
        ),
        "limit": 500
    }
    return get_meta_pages(url, params)

def get_meta_insights(account_id, since, until):
    url = f"{META_BASE}/{account_id}/insights"
    params = {
        "access_token": META_TOKEN,
        "level": "ad",
        "time_increment": 1,
        "breakdowns": "country",
        "time_range": json.dumps({
            "since": since,
            "until": until
        }),
        "fields": (
            "campaign_id,adset_id,ad_id,"
            "spend,impressions,clicks,actions,action_values"
        ),
        "limit": 500
    }
    return get_meta_pages(url, params)

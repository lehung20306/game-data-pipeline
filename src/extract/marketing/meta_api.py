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
            logger.warning(
                "Meta rate limit reached. Attempt %d/4. Retrying in 60 seconds.",
            )
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
    config_path = BASE_DIR / "config" / "account_mapping.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    accounts = []
    for account_id, info in config["meta"].items():
        accounts.append({
            "account_id": str(account_id),
            "api_id": f"act_{account_id}",
            "game": info["game"],
            "os": info["os"]
        })
    return accounts


def get_meta_campaigns(account_id):
    url = f"{META_BASE}/{account_id}/campaigns"
    params = {
        "access_token": META_TOKEN,
        "fields": (
            "id,name,account_id,effective_status,"
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
            "id,name,account_id,campaign_id,"
            "effective_status,optimization_goal,"
            "targeting,promoted_object"
        ),
        "limit": 500
    }
    return get_meta_pages(url, params)

def get_meta_ads(account_id):
    url = f"{META_BASE}/{account_id}/ads"
    params = {
        "access_token": META_TOKEN,
        "fields": (
            "id,name,account_id,adset_id,campaign_id,"
            "effective_status,creative{id,name,object_type}"
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
            "account_id,campaign_id,campaign_name,"
            "adset_id,adset_name,ad_id,ad_name,"
            "spend,impressions,clicks,actions,action_values"
        ),
        "limit": 500
    }
    return get_meta_pages(url, params)

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
TIKTOK_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")
TIKTOK_HEADERS = {"Access-Token": TIKTOK_TOKEN}
TIKTOK_BASE = os.getenv("TIKTOK_BASE").rstrip("/")
logger = logging.getLogger(__name__)

def tiktok_get(path, params):
    while True:
        body = requests.get(TIKTOK_BASE + path, headers=TIKTOK_HEADERS, params=params, timeout=60).json()
        if body["code"] == 0:
            return body["data"]                      
        if body["code"] == 40100:                       
            logger.warning("Tiktok rate limit reached. Retrying in 60 seconds.")
            time.sleep(60)
            continue
        raise RuntimeError(f"Tiktok API error {body['code']}: {body['message']}")

def get_tiktok_pages(path, params):
    rows = []
    page = 1
    params = dict(params or {})
    params.setdefault("page_size", 100)
    while True:
        params["page"] = page
        # tiktok_get() returns body["data"].
        data = tiktok_get(path, params)
        rows.extend(data.get("list", []))
        page_info = data.get("page_info", {})
        total_pages = int(page_info.get("total_page", 1))
        logger.info(
            "TikTok page %d/%d fetched, total rows: %d",
            page,
            total_pages,
            len(rows)
        )
        if page >= total_pages:
            break
        page += 1
    return rows

def get_tiktok_advertisers():
    config_path = BASE_DIR / "config" / "account_mapping.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    advertisers = []
    for advertiser_id, info in config["tiktok"].items():
        advertisers.append({
            "advertiser_id": str(advertiser_id),
            "game": info["game"],
            "os": info["os"]
        })
    return advertisers

def get_tiktok_campaigns(advertiser_id):
    path = "/campaign/get/"
    params = {
        "advertiser_id": str(advertiser_id),
        "fields": json.dumps([
            "campaign_id",
            "campaign_name",
            "budget",
            "budget_mode",
            "operation_status",
            "secondary_status",
            "create_time",
            "modify_time"
        ]),
        "page_size": 1000
    }
    return get_tiktok_pages(path, params)   

def get_tiktok_adgroups(advertiser_id):
    path = "/adgroup/get/"
    params = {
        "advertiser_id": str(advertiser_id),
        "fields": json.dumps([
            "adgroup_id",
            "adgroup_name",
            "campaign_id",
            "app_id",
            "app_download_url",
            "app_type",
            "location_ids",
            "age_groups",
            "gender",
            "operating_systems",
            "audience_type",
            "optimization_goal",
            "operation_status",
            "secondary_status",
            "schedule_start_time",
            "schedule_end_time"
        ]),
        "page_size": 1000
    }
    return get_tiktok_pages(path, params)

def get_tiktok_ads(advertiser_id):
    path = "/ad/get/"
    params = {
        "advertiser_id": str(advertiser_id),
        "fields": json.dumps([
            "ad_id",
            "ad_name",
            "adgroup_id",
            "campaign_id",
            "ad_format",
            "operation_status",
            "secondary_status",
            "video_id",
            "image_ids",
            "playable_url",
            "create_time",
            "modify_time"
        ]),
        "page_size": 1000
    }
    return get_tiktok_pages(path, params)

def get_tiktok_reporting(advertiser_id, since, until):
    path = "/report/integrated/get/"
    params = {
        "advertiser_id": str(advertiser_id),
        "service_type": "AUCTION",
        "report_type": "BASIC",
        "data_level": "AUCTION_AD",
        "dimensions": json.dumps([
            "ad_id",
            "stat_time_day",
            "country_code"
        ]),
        "metrics": json.dumps([
            "campaign_id",
            "adgroup_id",
            "spend",
            "impressions",
            "clicks",
            "conversion",
            "purchase",
            "total_purchase_value"
        ]),
        "start_date": since,
        "end_date": until,
        "page_size": 1000
    }
    return get_tiktok_pages(path, params)
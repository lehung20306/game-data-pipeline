import os
import time
import requests
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

from src.pipeline_logging import AdsAPIError

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")
TIKTOK_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")
TIKTOK_HEADERS = {"Access-Token": TIKTOK_TOKEN}
TIKTOK_BASE = os.getenv("TIKTOK_BASE").rstrip("/")
logger = logging.getLogger(__name__)

def tiktok_get(path, params=None):
    while True:
        body = requests.get(TIKTOK_BASE + path, headers=TIKTOK_HEADERS, params=params, timeout=60).json()
        if body["code"] == 0:
            return body["data"]                      
        if body["code"] == 40100:                       
            logger.warning("Rate limit reached | platform=tiktok api_code=40100 retry_in_s=60")
            time.sleep(60)
            continue
        raise AdsAPIError("tiktok", body["code"])

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
        logger.debug(
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
    return tiktok_get("/oauth2/advertiser/get/")["list"]

def get_tiktok_campaigns(advertiser_id):
    path = "/campaign/get/"
    params = {
        "advertiser_id": str(advertiser_id),
        "page_size": 1000
    }
    return get_tiktok_pages(path, params)   

def get_tiktok_adgroups(advertiser_id):
    path = "/adgroup/get/"
    params = {
        "advertiser_id": str(advertiser_id),
        "page_size": 1000
    }
    return get_tiktok_pages(path, params)

def get_tiktok_ads(advertiser_id):
    path = "/ad/get/"
    params = {
        "advertiser_id": str(advertiser_id),
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


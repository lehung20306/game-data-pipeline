import os
import time
import requests
import yaml

from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]

load_dotenv(BASE_DIR / ".env")

META_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_BASE = os.getenv("META_BASE", "").rstrip("/")


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


def meta_get(url, params):

    for attempt in range(4):

        response = requests.get(
            url,
            params=params,
            timeout=60
        )

        body = response.json()

        if "error" not in body:
            response.raise_for_status()
            return body

        if body["error"].get("code") == 17 and attempt < 3:

            print("Rate limit reached. Retrying in 60 seconds...")
            time.sleep(60)
            continue

        raise RuntimeError(f"Meta API error: {body['error']}")

    raise RuntimeError("Meta API request failed after retries")


def extract_meta():

    accounts = get_meta_accounts()

    print(f"Total accounts: {len(accounts)}")

    for account in accounts:

        account_id = account["account_id"]
        api_id = account["api_id"]
        game = account["game"]
        os_name = account["os"]

        print(f"Processing: {game} ({os_name})")
        print(f"Account ID: {account_id}")
        print(f"API ID: {api_id}")
        print("-" * 40)

        # TODO: Fetch daily ad reports for this account.
        # TODO: Handle report pagination.
        # TODO: Pass the extracted records to the Bronze loader.


if __name__ == "__main__":
    extract_meta()
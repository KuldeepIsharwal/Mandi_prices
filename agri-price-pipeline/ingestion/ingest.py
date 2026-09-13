import os
import sys
import time
import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

from config import get_api_key

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
API_KEY = get_api_key()
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

PAGE_SIZE = 1000
IST = timezone(timedelta(hours=5, minutes=30))
LOOKBACK_DAYS = 3  # re-check last N days each run - catches late/revised data, cheap since upsert handles dupes

TARGETS = [
    {"commodity": "Onion", "state": "Maharashtra", "district": "Nashik"},
    {"commodity": "Potato", "state": "West Bengal", "district": "Hooghly"},
    {"commodity": "Tomato", "state": "Karnataka", "district": "Kolar"},
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def load_database_url() -> str:
    """Load DATABASE_URL from .env locally, or from real env vars in CI."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    workspace_root = project_root.parent

    for env_path in (project_root / ".env", workspace_root / ".env"):
        if env_path.exists():
            load_dotenv(env_path)

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set (checked .env and environment).")
        sys.exit(1)
    return db_url


def convert_date(raw_date):
    """Convert DD/MM/YYYY -> YYYY-MM-DD"""
    try:
        d, m, y = raw_date.split("/")
        return f"{y}-{m}-{d}"
    except Exception:
        return None


def target_dates(lookback_days):
    """Last N days (DD/MM/YYYY, matching the API's filter format), skipping today."""
    today_ist = datetime.now(IST).date()
    return [
        (today_ist - timedelta(days=i)).strftime("%d/%m/%Y")
        for i in range(1, lookback_days + 1)
    ]


def fetch_page(commodity, state, district, offset, date_str=None, max_retries=3):
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": PAGE_SIZE,
        "offset": offset,
        "filters[Commodity]": commodity,
        "filters[State]": state,
        "filters[District]": district,
    }
    if date_str:
        params["filters[Arrival_Date]"] = date_str

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.warning(f"fetch attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                raise
            time.sleep(2 * attempt)


def parse_record(rec):
    date = convert_date(rec.get("Arrival_Date", ""))
    if date is None:
        return None
    try:
        min_price = float(rec.get("Min_Price") or 0)
        max_price = float(rec.get("Max_Price") or 0)
        modal_price = float(rec.get("Modal_Price") or 0)
    except ValueError:
        min_price = max_price = modal_price = None

    return (
        date,
        rec.get("State"),
        rec.get("District"),
        rec.get("Market"),
        rec.get("Commodity"),
        rec.get("Variety"),
        rec.get("Grade"),
        min_price,
        max_price,
        modal_price,
    )


def upsert_records(conn, rows):
    if not rows:
        return
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO mandi_prices
                (date, state, district, market, commodity, variety, grade, min_price, max_price, modal_price)
            VALUES %s
            ON CONFLICT (date, market, commodity, variety)
            DO UPDATE SET
                grade = EXCLUDED.grade,
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                modal_price = EXCLUDED.modal_price
            """,
            rows,
        )
    conn.commit()


def ingest_target(conn, target, date_str=None):
    """Pull one commodity/state/district. If date_str given, scoped to that
    single day; if None, does a full historical pull (use --full only)."""
    commodity, state, district = target["commodity"], target["state"], target["district"]
    label = f"{commodity} | {state} | {district}" + (f" | {date_str}" if date_str else " | FULL")
    logger.info(f"--- Ingesting {label} ---")

    offset = 0
    total_pulled = 0
    total_available = None

    while True:
        data = fetch_page(commodity, state, district, offset, date_str=date_str)

        if total_available is None:
            total_available = int(data.get("total", 0))
            logger.info(f"  Total available: {total_available}")

        records = data.get("records", [])
        if not records:
            break

        rows = [parse_record(r) for r in records]
        rows = [r for r in rows if r is not None]
        upsert_records(conn, rows)

        total_pulled += len(records)
        logger.info(f"  Pulled {total_pulled}/{total_available} (offset={offset})")

        offset += PAGE_SIZE
        if offset >= total_available:
            break

        time.sleep(0.3)  # be polite to the API

    logger.info(f"Done: {label} -> {total_pulled} records")
    return total_pulled


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full", action="store_true",
        help="Full historical pull per target, no date filter. For manual backfills only - do not use in the daily cron.",
    )
    parser.add_argument(
        "--date", help="Single date DD/MM/YYYY to ingest, overrides the lookback window.",
    )
    args = parser.parse_args()

    db_url = load_database_url()
    conn = psycopg2.connect(db_url)

    if args.full:
        dates = [None]
    elif args.date:
        dates = [args.date]
    else:
        dates = target_dates(LOOKBACK_DAYS)

    failures = []
    try:
        for target in TARGETS:
            try:
                for date_str in dates:
                    ingest_target(conn, target, date_str=date_str)
            except Exception as e:
                logger.error(f"FAILED target {target}: {e}")
                failures.append(target)
    finally:
        conn.close()

    if failures:
        logger.error(f"{len(failures)} target(s) failed: {failures}")
        sys.exit(1)

    logger.info("All targets ingested successfully.")


if __name__ == "__main__":
    main()
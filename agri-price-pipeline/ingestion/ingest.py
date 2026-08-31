import sqlite3
import os
import time
import requests

from config import get_api_key

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
API_KEY = get_api_key()
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "mandi_prices.db")
PAGE_SIZE = 1000  # records per request

# Locked scope
TARGETS = [
    {"commodity": "Onion", "state": "Maharashtra", "district": "Nashik"},
    {"commodity": "Potato", "state": "West Bengal", "district": "Hooghly"},
    {"commodity": "Tomato", "state": "Karnataka", "district": "Kolar"},
]


def convert_date(raw_date):
    """Convert DD/MM/YYYY -> YYYY-MM-DD"""
    try:
        d, m, y = raw_date.split("/")
        return f"{y}-{m}-{d}"
    except Exception:
        return None


def fetch_page(commodity, state, district, offset):
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": PAGE_SIZE,
        "offset": offset,
        "filters[Commodity]": commodity,
        "filters[State]": state,
        "filters[District]": district,
    }
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.json()


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
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO mandi_prices
            (date, state, district, market, commodity, variety, grade, min_price, max_price, modal_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date, market, commodity, variety)
        DO UPDATE SET
            grade=excluded.grade,
            min_price=excluded.min_price,
            max_price=excluded.max_price,
            modal_price=excluded.modal_price
        """,
        rows,
    )
    conn.commit()


def ingest_target(conn, target):
    commodity, state, district = target["commodity"], target["state"], target["district"]
    print(f"\n--- Ingesting {commodity} | {state} | {district} ---")

    offset = 0
    total_pulled = 0
    total_available = None

    while True:
        data = fetch_page(commodity, state, district, offset)

        if total_available is None:
            total_available = int(data.get("total", 0))
            print(f"Total available: {total_available}")

        records = data.get("records", [])
        if not records:
            break

        rows = [parse_record(r) for r in records]
        rows = [r for r in rows if r is not None]
        upsert_records(conn, rows)

        total_pulled += len(records)
        print(f"  Pulled {total_pulled}/{total_available} (offset={offset})")

        offset += PAGE_SIZE
        if offset >= total_available:
            break

        time.sleep(0.3)  # be polite to the API

    print(f"Done: {commodity} | {state} | {district} -> {total_pulled} records")


def main():
    conn = sqlite3.connect(DB_PATH)
    for target in TARGETS:
        ingest_target(conn, target)
    conn.close()
    print("\nAll targets ingested.")


if __name__ == "__main__":
    main() 
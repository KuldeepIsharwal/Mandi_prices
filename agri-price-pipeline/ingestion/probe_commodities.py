import requests
import time

from config import get_api_key

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
API_KEY = get_api_key()
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Candidate (commodity, state, district) combos to test
CANDIDATES = [
    ("Onion", "Maharashtra", "Nashik"),
    ("Potato", "West Bengal", "Hooghly"),
    ("Potato", "Uttar Pradesh", "Agra"),
    ("Tomato", "Karnataka", "Kolar"),
    ("Guar", "Rajasthan", "Jodhpur"),
    ("Guar", "Rajasthan", "Sri Ganganagar"),
    ("Moath", "Rajasthan", "Jodhpur"),
    ("Moath", "Rajasthan", "Nagaur"),
]

for commodity, state, district in CANDIDATES:
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 1,
        "filters[Commodity]": commodity,
        "filters[State]": state,
        "filters[District]": district,
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
        data = resp.json()
        total = data.get("total", "N/A")
        count = data.get("count", 0)
        sample = data.get("records", [])
        print(f"{commodity:10s} | {state:15s} | {district:15s} -> total={total}, got={count}")
        if sample:
            print(f"    sample date: {sample[0].get('Arrival_Date')}")
    except Exception as e:
        print(f"{commodity:10s} | {state:15s} | {district:15s} -> ERROR: {e}")
    time.sleep(0.5)  # be polite to the API
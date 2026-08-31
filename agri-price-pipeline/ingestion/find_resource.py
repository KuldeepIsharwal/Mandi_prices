import requests

from config import get_api_key

RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
API_KEY = get_api_key()

url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
params = {
    "api-key": API_KEY,
    "format": "json",
    "limit": 5,
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("Requesting...")
response = requests.get(url, params=params, headers=headers, timeout=30)
print("Status code:", response.status_code)
print(response.json())
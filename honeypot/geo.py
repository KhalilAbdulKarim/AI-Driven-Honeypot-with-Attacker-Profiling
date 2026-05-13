import requests
from functools import lru_cache

LOCAL_IPS = {"127.0.0.1", "::1", "localhost"}

FALLBACK = {
    "country": "Local",
    "countryCode": "LO",
    "city": "Loopback",
    "lat": 0.0,
    "lon": 0.0,
    "isp": "localhost",
}

# maxsize limits memory usage; it will automatically discard the oldest entries
@lru_cache(maxsize=1024)
def lookup(ip: str) -> dict:
    if not ip or ip in LOCAL_IPS:
        return FALLBACK

    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "country,countryCode,city,lat,lon,isp,status"},
            timeout=5,
        )
        
        # Check for rate limiting (HTTP 429)
        if resp.status_code == 429:
            print(f"[geo] Rate limit exceeded.")
            return FALLBACK
            
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "success":
            return data
            
    except requests.exceptions.RequestException as e:
        print(f"[geo] Network error for {ip}: {e}")
    except Exception as e:
        print(f"[geo] Unexpected error for {ip}: {e}")

    return FALLBACK
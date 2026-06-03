import json
import time
import requests
from pathlib import Path

_CACHE_FILE = Path(__file__).parent.parent / "data" / "geo_cache.json"
_cache: dict = {}
_loaded = False

LOCAL_IPS = {"127.0.0.1", "::1", "localhost"}

FALLBACK = {
    "country":     "Local",
    "countryCode": "LO",
    "city":        "Loopback",
    "lat":         0.0,
    "lon":         0.0,
    "isp":         "localhost",
}


def _load_cache():
    global _cache, _loaded
    if _loaded:
        return
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE) as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    _loaded = True


def _save_cache():
    try:
        _CACHE_FILE.parent.mkdir(exist_ok=True)
        with open(_CACHE_FILE, "w") as f:
            json.dump(_cache, f)
    except Exception:
        pass


def lookup(ip: str) -> dict:
    if ip in LOCAL_IPS or ip.startswith("127."):
        return FALLBACK

    _load_cache()

    if ip in _cache:
        return _cache[ip]

    for attempt in range(3):
        try:
            resp = requests.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "country,countryCode,city,lat,lon,isp,status"},
                timeout=5,
            )
            data = resp.json()
            if data.get("status") == "success":
                _cache[ip] = data
                _save_cache()
                return data
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            else:
                print(f"[geo] lookup failed for {ip} after 3 attempts: {e}")

    return FALLBACK
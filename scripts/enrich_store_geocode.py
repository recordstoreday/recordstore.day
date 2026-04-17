#!/usr/bin/env python3
"""Enrich store records with latitude/longitude based on addresses."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATA_PATH = Path("data/japan_rsd_2026_summary.json")
CACHE_PATH = Path("data/geocode_cache.json")
NOMINATIM_UA = "recordstoreday-data-bot/1.0 (contact: rsd@example.com)"


def normalize_address(address: str) -> str:
    text = address.strip()
    text = re.sub(r"^〒?\d{3}-?\d{4}\s*", "", text)
    return text


def load_cache() -> dict[str, dict[str, float | None]]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict[str, dict[str, float | None]]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True))


def geocode_japan_gsi(query: str) -> tuple[float | None, float | None]:
    url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?{urlencode({'q': query})}"
    with urlopen(url, timeout=30) as res:
        payload = json.loads(res.read().decode("utf-8"))
    if not payload:
        return None, None
    lon, lat = payload[0]["geometry"]["coordinates"]
    return float(lat), float(lon)


def geocode_nominatim(query: str) -> tuple[float | None, float | None]:
    params = urlencode({"q": query, "format": "jsonv2", "limit": 1})
    req = Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": NOMINATIM_UA, "Accept-Language": "ja,en"},
    )
    with urlopen(req, timeout=60) as res:
        payload = json.loads(res.read().decode("utf-8"))
    if not payload:
        return None, None
    return float(payload[0]["lat"]), float(payload[0]["lon"])


def geocode_store(prefecture: str, name: str, address: str) -> tuple[float | None, float | None]:
    if prefecture != "海外":
        for query in [f"{address} {name}", address]:
            try:
                lat, lon = geocode_japan_gsi(query)
                if lat is not None and lon is not None:
                    return lat, lon
            except Exception:
                continue
    for query in [f"{address} {name}", address]:
        try:
            lat, lon = geocode_nominatim(query)
            if lat is not None and lon is not None:
                return lat, lon
        except Exception:
            time.sleep(1.2)
            continue
        time.sleep(1.2)
    return None, None


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    cache = load_cache()

    total = len(data.get("store_records", []))
    for idx, store in enumerate(data.get("store_records", []), start=1):
        address = normalize_address(str(store.get("address", "")))
        name = str(store.get("name", ""))
        prefecture = str(store.get("prefecture", ""))

        if not address:
            store["latitude"] = None
            store["longitude"] = None
            continue

        key = f"{prefecture}|{name}|{address}"
        if key not in cache:
            lat, lon = geocode_store(prefecture, name, address)
            cache[key] = {"latitude": lat, "longitude": lon}

        store["latitude"] = cache[key]["latitude"]
        store["longitude"] = cache[key]["longitude"]

        if idx % 50 == 0 or idx == total:
            print(f"processed {idx}/{total}", flush=True)

    save_cache(cache)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch and normalize Record Store Day Japan 2026 stores/items JSON."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

DATA_PATH = Path("data/japan_rsd_2026_summary.json")
STORE_URL = "https://recordstoreday.jp/store_list/"
ITEM_URL = "https://recordstoreday.jp/itemyear/item2026/"
UA = "Mozilla/5.0 (compatible; recordstoreday-data-bot/1.0)"


def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=60) as res:
        return res.read().decode("utf-8", "ignore")


def clean_text(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_stores(html: str) -> list[dict[str, str | int | None]]:
    records: list[dict[str, str | int | None]] = []
    section_re = re.compile(
        r'<(?:div|section)[^>]*class="block01"[^>]*>(.*?)</(?:div|section)>',
        re.DOTALL | re.IGNORECASE,
    )
    pref_re = re.compile(r'<h5[^>]*class="tit-03"[^>]*>.*?</i>(.*?)</h5>', re.DOTALL | re.IGNORECASE)
    li_re = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)

    for section_html in section_re.findall(html):
        pref_match = pref_re.search(section_html)
        prefecture = clean_text(pref_match.group(1)) if pref_match else None
        for li_html in li_re.findall(section_html):
            name_match = re.search(
                r'<h5[^>]*class="tit-05"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</h5>',
                li_html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            thumb_match = re.search(
                r'<img[^>]*src="([^"]+)"',
                li_html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if not name_match:
                continue
            detail_url, name_raw = name_match.groups()
            address_match = re.search(
                r"<span>住所\s*:\s*</span>\s*(.*?)\s*<br\s*/?>",
                li_html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            phone_match = re.search(
                r"<span>電話番号\s*:\s*</span>\s*([^<\n]+)",
                li_html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            records.append(
                {
                    "record_type": "store",
                    "record_id": len(records) + 1,
                    "prefecture": prefecture,
                    "name": clean_text(name_raw),
                    "address": clean_text(address_match.group(1)) if address_match else "",
                    "phone": clean_text(phone_match.group(1)) if phone_match else "",
                    "thumbnail_url": thumb_match.group(1) if thumb_match else "",
                    "detail_url": detail_url,
                }
            )
    return records


def parse_items(html: str) -> list[dict[str, str | int | None]]:
    records: list[dict[str, str | int | None]] = []
    li_re = re.compile(r'<li\s+class="item[^\"]*"[^>]*>(.*?)</li>', re.DOTALL | re.IGNORECASE)
    for li_html in li_re.findall(html):
        artist_match = re.search(r"<h3>(.*?)</h3>", li_html, flags=re.DOTALL | re.IGNORECASE)
        link_match = re.search(r'<a\s+href="([^"]+)"', li_html, flags=re.IGNORECASE)
        thumb_match = re.search(r'<img[^>]*src="([^"]+)"', li_html, flags=re.IGNORECASE)
        format_match = re.search(r"<span[^>]*>(.*?)</span>", li_html, flags=re.DOTALL | re.IGNORECASE)
        if not artist_match or not link_match:
            continue

        artist = clean_text(artist_match.group(1))
        after_h3 = li_html[artist_match.end() :]
        title = clean_text(after_h3)
        if not artist and not title:
            continue

        records.append(
            {
                "record_type": "item",
                "record_id": len(records) + 1,
                "artist": artist,
                "title": title,
                "format": clean_text(format_match.group(1)) if format_match else "",
                "thumbnail_url": thumb_match.group(1) if thumb_match else "",
                "detail_url": link_match.group(1),
            }
        )
    return records


def main() -> None:
    store_html = fetch_html(STORE_URL)
    item_html = fetch_html(ITEM_URL)
    stores = parse_stores(store_html)
    items = parse_items(item_html)

    payload = {
        "source_urls": [STORE_URL, ITEM_URL],
        "fetched_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "country": "Japan",
        "event_year": 2026,
        "record_definition": "1レコード = 店舗情報1件 または アイテム情報1件",
        "store_records": stores,
        "item_records": items,
        "record_counts": {
            "store_records": len(stores),
            "item_records": len(items),
            "total_records": len(stores) + len(items),
        },
    }

    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

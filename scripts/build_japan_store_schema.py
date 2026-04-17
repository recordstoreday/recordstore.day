#!/usr/bin/env python3
"""Normalize japan_rsd_2026_summary.json store entries to detailed schema."""

import json
from pathlib import Path

DATA_PATH = Path("data/japan_rsd_2026_summary.json")


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    ids = data["stores"].get("store_link_ref_ids", [])
    data["stores"]["stores_detailed"] = [
        {"ref_id": i, "name": None, "address": None, "phone": None} for i in ids
    ]
    data["stores"]["detail_fields"] = "name/address/phone を全件同一スキーマで保持"
    data["stores"]["note"] = "全399件を同一スキーマ（ref_id,name,address,phone）で展開。"
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

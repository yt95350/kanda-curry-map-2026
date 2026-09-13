#!/usr/bin/env python3
"""公開前の安全弁：店舗数が前回公開分より1割以上減っていたら異常とみなして止める"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
new = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))["stores"]
prev_path = os.path.join(os.environ.get("OUT_DIR") or os.path.join(HERE, "..", "app"), "data.json")
if os.path.exists(prev_path):
    prev = json.load(open(prev_path, encoding="utf-8"))["stores"]
    if len(new) < len(prev) * 0.9:
        sys.exit(f"店舗数が急減しています（前回 {len(prev)} → 今回 {len(new)}）。公式サイトの構造が変わった可能性があるため中止します。")
    print(f"店舗数チェック OK: 前回 {len(prev)} → 今回 {len(new)}")
else:
    print(f"前回データなし。今回 {len(new)} 店")
missing = [s["name"] for s in new if not s.get("lat")]
if missing: sys.exit("座標のない店があります: " + ", ".join(missing))

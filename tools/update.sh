#!/bin/sh
# 公式サイトから店舗情報を取り直して地図を作り直す。
#   ローカル: sh tools/update.sh            → ../app/ に出力
#   CI(GitHub Actions): OUT_DIR=. sh tools/update.sh → リポジトリ直下に出力
set -e
cd "$(dirname "$0")"
python3 scrape.py       # 参加店一覧・各店ページを取得 → stores_raw.json
python3 geocode.py      # 座標が無い店だけ goo.gl 解決 / 国土地理院APIで推定（geocache.json）
python3 build_data.py   # 整形 + 営業時間解析 + ガイドブック頁 → data.json
python3 check.py        # 店舗数が前回より大きく減っていたら失敗させる（壊れたデータを公開しない）
python3 build.py        # index.html / full.html / lite.html / KML / CSV を生成

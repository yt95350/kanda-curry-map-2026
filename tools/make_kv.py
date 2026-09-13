#!/usr/bin/env python3
"""SNS用キービジュアル（app/og.png 2400x1260、docs/キービジュアル_1200x630.jpg）を生成。
URL は tools/site.json の base_url を使う。アプリの画面写真は tools/kv-phone.png（差し替え可）。"""
import os, json, base64, tempfile, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); from shot import shot
from PIL import Image
base = json.load(open(os.path.join(HERE, "site.json"), encoding="utf-8"))["base_url"]
url_text = base.replace("https://", "").replace("http://", "").rstrip("/")
phone = "data:image/png;base64," + base64.b64encode(open(os.path.join(HERE, "kv-phone.png"), "rb").read()).decode()
html = open(os.path.join(HERE, "kv.template.html"), encoding="utf-8").read().replace("{{phone}}", phone).replace("{{url}}", url_text)
tmp = os.path.join(tempfile.mkdtemp(prefix="kv-"), "kv.html"); open(tmp, "w", encoding="utf-8").write(html)
out = os.path.join(HERE, "..", "app", "og.png")
shot("file://" + tmp, out, 1200, 630, 2)
Image.open(out).convert("RGB").save(os.path.join(HERE, "..", "docs", "キービジュアル_1200x630.jpg"), quality=90, optimize=True)
print("wrote app/og.png and docs/キービジュアル_1200x630.jpg with URL:", url_text)

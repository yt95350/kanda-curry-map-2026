import json, html, os, csv
SCRATCH = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get("OUT_DIR") or os.path.join(SCRATCH, "..", "app")
os.makedirs(APP, exist_ok=True)
data = json.load(open(os.path.join(SCRATCH, "data.json"), encoding="utf-8"))
tpl = open(os.path.join(SCRATCH, "index.template.html"), encoding="utf-8").read()

BASE_URL = json.load(open(os.path.join(SCRATCH, "site.json"), encoding="utf-8"))["base_url"]
def build(media, fname):
    d = dict(data); d["media"] = media
    stores = []
    for s in data["stores"]:
        s = dict(s)
        if not media:
            for k in ("thumb", "img", "face", "owner", "desc"): s.pop(k, None)
            s["desc"] = []
        stores.append(s)
    d["stores"] = stores
    js = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = tpl.replace("/*__DATA__*/null", js)
    out = out.replace("/*__OGURL__*/", BASE_URL if fname == "index.html" else BASE_URL + fname)
    out = out.replace("https://yt95350.github.io/kanda-curry-map-2026/og.png", BASE_URL + "og.png")
    open(os.path.join(APP, fname), "w", encoding="utf-8").write(out)
    print(fname, len(out) // 1024, "KB")

# 2026-09-12 委員会（委員長）から、非商用かつ引用元記載を条件に写真つき版の拡散を了承いただいたため、
# 写真つき版をトップ（index.html）にする。full.html は旧リンク・QR用の同内容、lite.html は写真なし版。
build(True, "index.html")
build(True, "full.html")
build(False, "lite.html")

# KML for Google My Maps
def kml_color(hexc):  # aabbggrr
    r, g, b = hexc[1:3], hexc[3:5], hexc[5:7]
    return "ff" + b + g + r
k = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
     '<name>神田カレーグランプリ2026 参加店（非公式）</name>']
for cid, c in data["cats"].items():
    k.append(f'<Style id="{cid}"><IconStyle><color>{kml_color(c["color"])}</color><scale>1.1</scale><Icon><href>http://maps.google.com/mapfiles/kml/paddle/wht-blank.png</href></Icon></IconStyle></Style>')
for cid, c in data["cats"].items():
    k.append(f'<Folder><name>{html.escape(c["name"])}</name>')
    for s in data["stores"]:
        if f'c{s["cat"]}' != cid: continue
        desc = []
        if s["menu"]: desc.append("【メニュー】\n" + "\n".join(s["menu"]))
        if s["hours"]: desc.append("【営業時間】\n" + s["hours"])
        if s["closed"]: desc.append("【定休日】" + s["closed"])
        if s["station"]: desc.append("【最寄駅】\n" + s["station"])
        if s["addr"]: desc.append("【住所】" + s["addr"])
        if s["tel"]: desc.append("【電話】" + s["tel"])
        if s["notice"]: desc.append("【お知らせ】\n" + s["notice"])
        desc.append("公式ページ: " + s["url"])
        if s["approx"]: desc.append("※位置は住所からの推定（概算）")
        k.append(f'<Placemark><name>{html.escape(s["name"])}</name><styleUrl>#{cid}</styleUrl>'
                 f'<description><![CDATA[{html.escape(chr(10).join(desc)).replace(chr(10), "<br>")}]]></description>'
                 f'<Point><coordinates>{s["lng"]},{s["lat"]},0</coordinates></Point></Placemark>')
    k.append('</Folder>')
k.append('</Document></kml>')
open(os.path.join(APP, "kanda-curry-2026.kml"), "w", encoding="utf-8").write("\n".join(k))

# CSV (UTF-8 with BOM for Excel / Google My Maps import)
with open(os.path.join(APP, "kanda-curry-2026.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["店名", "カテゴリ", "緯度", "経度", "住所", "最寄駅", "メニュー", "営業時間", "定休日", "電話", "辛さ", "テイクアウト", "ガイドブックページ", "位置概算", "公式ページ"])
    for s in data["stores"]:
        w.writerow([s["name"], data["cats"][f'c{s["cat"]}']["name"], s["lat"], s["lng"], s["addr"], s["station"].replace("\n", " / "),
                    " / ".join(s["menu"]), s["hours"].replace("\n", " / "), s["closed"], s["tel"], s["spice"], s["takeout"],
                    s["page"] or "", "概算" if s["approx"] else "", s["url"]])
json.dump(data, open(os.path.join(APP, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote KML/CSV/data.json")

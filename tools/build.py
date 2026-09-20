import json, html, os, csv
SCRATCH = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get("OUT_DIR") or os.path.join(SCRATCH, "..", "app")
os.makedirs(APP, exist_ok=True)
data = json.load(open(os.path.join(SCRATCH, "data.json"), encoding="utf-8"))
tpl = open(os.path.join(SCRATCH, "index.template.html"), encoding="utf-8").read()

BASE_URL = json.load(open(os.path.join(SCRATCH, "site.json"), encoding="utf-8"))["base_url"]
# 検索エンジン向けの構造化データ（このページが何のイベントの地図かを伝える）
JSONLD = {"@context": "https://schema.org", "@type": "WebSite", "name": "神田カレーマップ2026（非公式）", "url": BASE_URL, "inLanguage": "ja",
          "description": "神田カレー街食べ歩きスタンプラリー2026の参加カレー店を地図と一覧から探せる非公式マップ",
          "about": {"@type": "Event", "name": "神田カレー街食べ歩きスタンプラリー2026", "startDate": "2026-08-01", "endDate": "2026-12-20",
                    "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                    "location": {"@type": "Place", "name": "神田・神保町・秋葉原・御茶ノ水周辺のカレー店", "address": {"@type": "PostalAddress", "addressRegion": "東京都", "addressLocality": "千代田区", "addressCountry": "JP"}},
                    "url": "https://kanda-curry.com/stamprally2026/"}}
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
    out = out.replace("/*__CANONICAL__*/", BASE_URL)  # full.html / lite.html は同内容なので、検索にはトップだけを出す
    out = out.replace("/*__JSONLD__*/", json.dumps(JSONLD, ensure_ascii=False).replace("</", "<\\/"))
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

# 参加店の一覧（テキスト版）。地図はJavaScriptで描くため、検索エンジンと読み上げ向けに静的なHTMLも用意する。
# 載せるのは事実情報だけ（写真と紹介文は地図のほうにだけ出す）。
def jdate(iso):
    y, m, d = iso.split("-"); return f"{y}年{int(m)}月{int(d)}日"
E = html.escape
n = len(data["stores"])
h = [f"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>神田カレー街スタンプラリー2026 参加店一覧（{n}店）｜神田カレーマップ（非公式）</title>
<meta name="description" content="神田カレー街食べ歩きスタンプラリー2026の参加カレー店{n}店を、欧風・インド・スープなどのカテゴリ別に一覧。住所、最寄駅、営業時間、定休日、メニューと価格。地図で探せる非公式マップつき。">
<link rel="canonical" href="{BASE_URL}stores.html"><meta property="og:image" content="{BASE_URL}og.png"><meta property="og:title" content="神田カレー街スタンプラリー2026 参加店一覧（非公式）">
<style>body{{font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",Meiryo,sans-serif;color:#2b241d;background:#fbf7f0;margin:0;line-height:1.7}}
main{{max-width:760px;margin:0 auto;padding:16px}}h1{{font-size:22px;line-height:1.4}}h2{{font-size:18px;margin:28px 0 8px;padding:6px 10px;background:#b4531d;color:#fff;border-radius:8px}}
article{{background:#fff;border:1px solid #e9e1d5;border-radius:10px;padding:10px 12px;margin:8px 0}}h3{{font-size:16px;margin:0 0 4px}}article p{{margin:2px 0;font-size:14px}}
a{{color:#b4531d}}.cta{{display:inline-block;background:#b4531d;color:#fff;text-decoration:none;font-weight:700;border-radius:999px;padding:10px 18px;margin:6px 0}}.muted{{color:#7a6f63;font-size:13px}}nav a{{display:inline-block;margin:0 8px 6px 0;font-size:14px}}</style></head><body><main>
<h1>神田カレー街食べ歩きスタンプラリー2026 参加店一覧（{n}店）</h1>
<p>神田カレーグランプリのスタンプラリー（2026年8月1日〜12月20日）に参加しているカレー店の一覧です。神田・神保町・秋葉原・御茶ノ水周辺の{n}店を、カテゴリ別にまとめています。個人が作った<b>非公式</b>のページで、主催者とは関係ありません。</p>
<p><a class="cta" href="./">🍛 地図で探す（現在地から近い順・営業中の目安・訪問チェック）</a></p>
<p class="muted">引用元：神田カレーグランプリ公式サイト（{jdate(data["updated"])}現在）。営業状況・メニュー・価格は変わることがあります。最新の情報は<a href="https://kanda-curry.com/stamprally2026/">公式サイト</a>と各店の案内をご確認ください。</p>
<nav>"""]
for cid, c in data["cats"].items():
    cnt = sum(1 for s in data["stores"] if f'c{s["cat"]}' == cid)
    if cnt: h.append(f'<a href="#{cid}">{E(c["name"])}（{cnt}）</a>')
h.append("</nav>")
for cid, c in data["cats"].items():
    ss = [s for s in data["stores"] if f'c{s["cat"]}' == cid]
    if not ss: continue
    h.append(f'<h2 id="{cid}">{E(c["name"])}カレー（{len(ss)}店）</h2>' if c["name"].endswith(("風", "ープ")) else f'<h2 id="{cid}">{E(c["name"])}（{len(ss)}店）</h2>')
    for s in ss:
        one = lambda t: E(" ／ ".join(x.strip() for x in str(t).split("\n") if x.strip()))
        h.append(f'<article><h3><a href="./#s={E(s["id"])}">{E(s["name"])}</a></h3>')
        if s.get("addr"): h.append(f'<p>住所：{one(s["addr"])}</p>')
        if s.get("station"): h.append(f'<p>最寄駅：{one(s["station"])}</p>')
        if s.get("hours"): h.append(f'<p>営業時間：{one(s["hours"])}' + (f'　定休日：{one(s["closed"])}' if s.get("closed") else "") + "</p>")
        if s.get("menu"): h.append(f'<p>メニュー：{E(" ／ ".join(s["menu"]))}</p>')
        h.append(f'<p class="muted"><a href="./#s={E(s["id"])}">地図で見る</a>　<a href="{E(s["url"])}" rel="noopener">公式サイトの店舗ページ</a></p></article>')
h.append(f'<p><a class="cta" href="./">🍛 地図で探す</a></p><p class="muted">神田カレーマップ2026（非公式）　引用元：神田カレーグランプリ公式サイト（{jdate(data["updated"])}現在）</p></main></body></html>')
open(os.path.join(APP, "stores.html"), "w", encoding="utf-8").write("\n".join(h))
open(os.path.join(APP, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"<url><loc>{BASE_URL}{u}</loc><lastmod>{data['updated']}</lastmod></url>\n" for u in ("", "stores.html")) + "</urlset>\n")
open(os.path.join(APP, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n")
print("wrote stores.html / sitemap.xml / robots.txt")

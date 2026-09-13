import os as _os; _os.chdir(_os.path.dirname(_os.path.abspath(__file__)))
import re, html, json, time, sys, os, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh) KandaCurryMapBot/0.1 (personal, non-commercial)"}
def get(url, retries=3):
    url = urllib.parse.quote(url, safe=":/?=&%")
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print("retry", url, e, file=sys.stderr); time.sleep(2)
    return ""

def clean(t):
    t = re.sub(r'<br\s*/?>', '\n', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = t.replace('　', ' ').replace('\xa0', ' ')
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    return t.strip()

# ---- 1. store list with categories from stamp rally page
s = get("https://kanda-curry.com/stamprally2026/")
open("stamprally.html", "w", encoding="utf-8").write(s)
CATS = {"c1":"欧風","c2":"北インド・パキスタン","c3":"東インド・ネパール","c4":"南インド・スリランカ",
        "c5":"東南アジア・中国","c6":"スープ","c7":"麺・パン","c8":"その他・オリジナル"}
stores = []
for cid, cname in CATS.items():
    a = s.find(f'id="{cid}"')
    nxt = f'id="c{int(cid[1:])+1}"'
    b = s.find(nxt)
    sec = s[a:b]
    for m in re.finditer(r'<div class="card Acourse">(.*?)</div>', sec, re.S):
        card = m.group(1)
        href = re.search(r'<a href="([^"]+)"', card)
        img = re.search(r'<img[^>]+src="([^"]+)"', card)
        name = re.search(r'<p class="cardtxt">\s*<a href="[^"]+">(.*?)</a>', card, re.S)
        if not href or not name: continue
        url = html.unescape(href.group(1)).strip().rstrip('"')
        stores.append({"category": cname, "cat_id": cid, "name_list": clean(name.group(1)),
                       "url": url, "thumb": html.unescape(img.group(1)) if img else None})
print("stores in list:", len(stores), file=sys.stderr)

# ---- 2. detail pages
def parse_detail(st):
    h = get(st["url"])
    d = dict(st)
    if not h:
        d["error"] = "fetch failed"; return d
    # table
    tbl = re.search(r'<table[^>]*class="hyou"[^>]*>(.*?)</table>', h, re.S)
    fields = {}
    if tbl:
        for th, td in re.findall(r'<tr>\s*<th>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>', tbl.group(1), re.S):
            k = clean(th).replace('\n', '')
            fields[k] = clean(td)
    d["fields"] = fields
    # title
    t = re.search(r'<h2 class="readcopy">(.*?)</h2>', h, re.S)
    d["name"] = clean(t.group(1)) if t else fields.get("店名", st["name_list"])
    # main image
    mg = re.search(r'<div id="mainGazou">\s*<img src="([^"]+)"', h)
    d["main_image"] = html.unescape(mg.group(1)) if mg else None
    # notice
    no = re.search(r'<div id="zoshirasebody">(.*?)</div>', h, re.S)
    d["notice"] = clean(no.group(1)) if no else ""
    # description block: from after zoshirase to google map link
    ml = h.find('id="mainLeft"')
    gm = h.find('https://www.google.com/maps', ml)
    body = h[ml:gm if gm > 0 else ml+20000]
    body = re.sub(r'<div id="zoshirase".*?</div>\s*</div>', '', body, flags=re.S)
    body = re.sub(r'<h2 class="readcopy">.*?</h2>', '', body, flags=re.S)
    # photo caption (owner)
    pc = re.search(r'<p class="photo[^"]*">(.*?)</p>', body, re.S)
    d["owner_caption"] = clean(pc.group(1)) if pc else ""
    face = re.search(r'<p class="photo[^"]*">.*?<img[^>]+src="([^"]+)"', body, re.S)
    d["face_image"] = html.unescape(face.group(1)) if face else None
    body = re.sub(r'<p class="photo[^"]*">.*?</p>', '', body, flags=re.S)
    # description: sequence of headings/paragraphs between title and map link (excluding h2.readcopy already removed)
    secs = []
    cur = None
    for tag, inner in re.findall(r'<(h[23]|p)(?:\s[^>]*)?>(.*?)</\1>', body, re.S):
        t = clean(inner)
        if not t: continue
        if tag.startswith('h'):
            cur = {"h": t, "p": ""}; secs.append(cur)
        else:
            if cur is None: cur = {"h": "", "p": ""}; secs.append(cur)
            cur["p"] = (cur["p"] + "\n" + t).strip() if cur["p"] else t
    d["sections"] = secs
    # any other images in body (menu photos)
    d["body_images"] = [html.unescape(x) for x in re.findall(r'<img[^>]+src="([^"]+)"', body) if 'uploads' in x]
    # google maps
    g = re.search(r'href="(https?://[^"]*google[^"]*/maps[^"]*)"', h) or re.search(r'href="(https?://(?:goo\.gl|maps\.app\.goo\.gl)/[^"]+)"', h) or re.search(r'href="(https?://maps\.google[^"]+)"', h)
    d["gmap_url"] = html.unescape(g.group(1)) if g else None
    lat = lng = None
    if d["gmap_url"]:
        m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', d["gmap_url"])
        if m: lat, lng = float(m.group(1)), float(m.group(2))
        else:
            m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', d["gmap_url"])
            if m: lat, lng = float(m.group(1)), float(m.group(2))
            else:
                m = re.search(r'[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)', d["gmap_url"])
                if m: lat, lng = float(m.group(1)), float(m.group(2))
    d["lat"], d["lng"] = lat, lng
    return d

with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(parse_detail, stores))

json.dump(results, open("stores_raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ok = sum(1 for r in results if r.get("lat"))
print("done", len(results), "with coords:", ok, file=sys.stderr)
for r in results:
    if not r.get("lat"):
        print("NO COORD:", r["name_list"], r["url"], r.get("gmap_url"), file=sys.stderr)

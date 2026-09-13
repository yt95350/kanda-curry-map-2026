import os as _os; _os.chdir(_os.path.dirname(_os.path.abspath(__file__)))
import json, re, urllib.request, urllib.parse, time, os
UA = {"User-Agent": "Mozilla/5.0"}
d = json.load(open("stores_raw.json", encoding="utf-8"))
cache_f = "geocache.json"
cache = json.load(open(cache_f, encoding="utf-8")) if os.path.exists(cache_f) else {}

def resolve_short(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA, method="HEAD"), timeout=20)
        return r.geturl()
    except Exception as e:
        return getattr(e, "url", None)

def gsi(addr):
    u = "https://msearch.gsi.go.jp/address-search/AddressSearch?q=" + urllib.parse.quote(addr)
    try:
        j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20))
        if j:
            lng, lat = j[0]["geometry"]["coordinates"]
            return lat, lng, j[0]["properties"]["title"]
    except Exception as e:
        print("gsi err", e)
    return None

def norm_addr(a):
    a = a.replace(" ", "").replace("　", "")
    a = re.sub(r'(?<=\d)[－―‐ーｰ](?=\d)', '-', a)
    a = re.sub(r'(\d+(?:-\d+){1,2})(.*)$', r'\1', a)
    if not a.startswith("東京都"): a = "東京都" + a
    return a

for x in d:
    if x.get("lat"): x["geo_src"] = "official"; continue
    key = x["url"]
    if key in cache:
        x.update(cache[key]); continue
    g = x.get("gmap_url")
    if g and "goo.gl" in g:
        full = resolve_short(g)
        m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', full or "") or re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', full or "")
        if m:
            cache[key] = {"lat": float(m.group(1)), "lng": float(m.group(2)), "geo_src": "goo.gl"}
            x.update(cache[key]); print("RESOLVED", x["name"]); continue
    addr = x.get("fields", {}).get("住所", "")
    na = norm_addr(addr)
    r = gsi(na); time.sleep(0.3)
    if r:
        approx = not re.search(r'号$', r[2])
        cache[key] = {"lat": r[0], "lng": r[1], "geo_title": r[2], "geo_src": "gsi", "approx": approx}
        x.update(cache[key]); print("GSI", x["name"], "|", na, "->", r[2], "approx" if approx else "")
    else:
        print("FAIL", x["name"], "|", addr)

json.dump(cache, open(cache_f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(d, open("stores_raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("with coords:", sum(1 for x in d if x.get("lat")), "/", len(d), "approx:", sum(1 for x in d if x.get("approx")))

import os as _os; _os.chdir(_os.path.dirname(_os.path.abspath(__file__)))
import os
import json, re, unicodedata, difflib, datetime
raw = json.load(open("stores_raw.json", encoding="utf-8"))
refs = json.load(open("pdf_refs.json", encoding="utf-8"))
CATS = {"c1":("欧風","#997916"),"c2":("北インド・パキスタン","#e66528"),"c3":("東インド・ネパール","#de162f"),
        "c4":("南インド・スリランカ","#be2c3b"),"c5":("東南アジア・中国","#920865"),"c6":("スープ","#185bac"),
        "c7":("麺・パン","#27a235"),"c8":("その他・オリジナル","#7e161a")}

def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r'[\s　〜～~・･\-–—‐ー_,.、。()（）〈〉<>《》「」『』\'’"&＆!！?？:：/／]', '', s)
    s = re.sub(r'(店|本店)$', '', s)
    return s

# ---- PDF page matching: nearest (P##) marker to a distinctive name key in normalized PDF text
import fitz
_pdf_candidates = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "kcgsr-2026-map.pdf"), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kcgsr-2026-map.pdf")]
_doc = fitz.open(next(p for p in _pdf_candidates if os.path.exists(p)))
_txt = "\n".join(p.get_text("text") for p in _doc)
_txt = re.sub(r'[（(]P?(\d{2})[）)]', lambda m: "§%s§" % m.group(1), _txt)
_txt = unicodedata.normalize("NFKC", _txt).lower()
_txt = re.sub(r'[\s　〜～~・･\-–—‐ー_,.、。()（）〈〉<>《》「」『』\'’"&＆!！?？:：/／]', '', _txt)
_markers = [(m.start(), int(m.group(1))) for m in re.finditer(r'§(\d{2})§', _txt)]
GENERIC = set("""カレー 欧風 欧風カレー インド パキスタン 料理 神田 神保町 秋葉原 店 本店 東京 tokyo レストラン restaurant カフェ cafe bar dining 食堂 キッチン kitchen curry spice
御茶ノ水 お茶の水 水道橋 九段下 飯田橋 岩本町 丸の内 有楽町 市ヶ谷 麹町 半蔵門 日本橋 小川町 外神田 スパイス タイ 中国 ネパール スリランカ 専門店 酒場 居酒屋 喫茶 ダイニング バル
インドパキスタン料理 インドアジアン料理 インド料理 タイ料理 中国料理 カレーショップ 神田店 神保町店 秋葉原店 御茶ノ水店 神田本店 神保町本店 秋葉原本店 music 2nd asian bistro""".split())
def keys_for(name, list_name):
    ks = set()
    for nm in (name, list_name):
        n = unicodedata.normalize("NFKC", nm)
        n = re.sub(r'[（(].*?[）)]', ' ', n)  # drop parenthesised parts
        for w in re.split(r'[\s　・･〜～~/／&＆]+', n):
            w = norm(w)
            if len(w) >= 3 and w not in GENERIC: ks.add(w)
        full = norm(n)
        if len(full) >= 3: ks.add(full)
    return ks
def find_page(store_name, list_name):
    votes = {}
    for k in keys_for(store_name, list_name):
        for m in re.finditer(re.escape(k), _txt):
            best = None
            for pos, p in _markers:
                dist = min(abs(pos - m.start()), abs(pos - m.end()))
                if dist <= 40 and (best is None or dist < best[0]): best = (dist, p)
            if best: votes[best[1]] = votes.get(best[1], 0) + len(k)
    if not votes: return (0, None)
    p = max(votes, key=votes.get)
    return (1.0, p)


# ---- 営業時間・定休日の解析（目安。原文は必ず併記する） ----
DAYCH = {"日":0,"月":1,"火":2,"水":3,"木":4,"金":5,"土":6}
DAYORD = "月火水木金土日"
ALLDAYS = [0,1,2,3,4,5,6,"h"]
HOLIDAYS_2026 = ["2026-07-20","2026-08-11","2026-09-21","2026-09-22","2026-09-23","2026-10-12","2026-11-03","2026-11-23","2027-01-01"]
_TIME = re.compile(r'(\d{1,2}):(\d{2})\s*[～〜~\-－ー–—]\s*(?:翌|L\.?O\.?)?\s*(\d{1,2}):(\d{2})', re.I)

def _nfkc(t):
    t = unicodedata.normalize("NFKC", t or "")
    return t.replace("：", ":").replace("\r", "")

def _parse_days(prefix):
    p = re.sub(r'(ランチ|ディナー|カフェ|タイム|時間|営業|曜日|曜|\s)', '', prefix)
    p = p.replace("祝日", "祝")
    days = set()
    if "平日" in p:
        days.update([1,2,3,4,5]); p = p.replace("平日", "")
    # ranges like 月～金
    for a, b in re.findall(r'([月火水木金土日])[～〜~\-－ー–—]([月火水木金土日])', p):
        i, j = DAYORD.index(a), DAYORD.index(b)
        if i <= j: days.update(DAYCH[c] for c in DAYORD[i:j+1])
    p = re.sub(r'[月火水木金土日][～〜~\-－ー–—][月火水木金土日]', '', p)
    for c in p:
        if c in DAYCH: days.add(DAYCH[c])
        elif c == "祝": days.add("h")
    return days or None

def parse_hours(text):
    rules, cur_days = [], None
    for line in _nfkc(text).split("\n"):
        line = line.strip()
        if not line or line.startswith(("※", "*", "・")): continue
        body = re.sub(r'[（(][^）)]*[）)]', ' ', line)   # (LO14:30) などを除去
        if "24時間" in body:
            rules.append({"d": ALLDAYS, "r": [[0, 1440]]}); continue
        m = _TIME.search(body)
        prefix = body[:m.start()] if m else body
        d = _parse_days(prefix)
        if d: cur_days = d
        if not m: continue
        ranges = []
        for h1, m1, h2, m2 in _TIME.findall(body):
            a, b = int(h1)*60+int(m1), int(h2)*60+int(m2)
            if b <= a: b += 1440
            if 0 <= a < 1440 and b - a <= 18*60: ranges.append([a, b])
        if not ranges: continue
        days = sorted(cur_days, key=lambda x: (isinstance(x, str), x)) if cur_days else ALLDAYS
        rules.append({"d": days, "r": ranges})
    return rules

def parse_closed(text):
    t = _nfkc(text)
    t = re.sub(r'[（(][^）)]*[）)]', ' ', t)
    if re.search(r'無休', t): return set(), []
    t = t.replace("祝日", "祝").replace("曜日", "").replace("曜", "")
    closed, nth = set(), []
    # 第1&第3土 のような複数指定を先に拾う
    for m in re.finditer(r'((?:第\d[&]?)+)([月火水木金土日])', t):
        for n in re.findall(r'\d', m.group(1)): nth.append([int(n), DAYCH[m.group(2)]])
    t = re.sub(r'((?:第\d[&]?)+)([月火水木金土日])', ' ', t)
    for tok in re.split(r'[、,・/&\n\s]+', t):
        if not tok: continue
        if re.search(r'ランチ|ディナー|夜|タイム|以外|不定|翌日|あり|こと|場合|ある', tok): continue
        m = re.fullmatch(r'第(\d)([月火水木金土日])', tok)
        if m: nth.append([int(m.group(1)), DAYCH[m.group(2)]]); continue
        if re.fullmatch(r'[月火水木金土日祝]+', tok):
            for c in tok: closed.add("h" if c == "祝" else DAYCH[c])
    return closed, nth

def build_sched(hours, closed_text):
    rules = parse_hours(hours)
    closed, nth = parse_closed(closed_text)
    return {"ok": bool(rules), "rules": rules, "closed": sorted(closed, key=lambda x: (isinstance(x, str), x)), "nth": nth}

# ---- 支払い方法：公式サイト本文から拾えたものと overrides.json ----
_PAY = re.compile(r'[^。\n※]*(現金|キャッシュレス|クレジット|カード|QR|PayPay|ペイペイ|電子マネー|交通系)[^。\n]*')
def extract_pay(x):
    texts = [x.get("notice", ""), x["fields"].get("お願い", ""), x["fields"].get("テイクアウトの補足", "")] + [sec["p"] for sec in x.get("sections", [])]
    for t in texts:
        m = _PAY.search(unicodedata.normalize("NFKC", t))
        if m:
            frag = m.group(0).strip(" 　・-")
            if 2 < len(frag) <= 40: return frag
    return ""
OVERRIDES = {}
try:
    OVERRIDES = json.load(open("overrides.json", encoding="utf-8")).get("stores", {})
except Exception: pass

out = []
seen_ids = set()
unmatched = []
for i, x in enumerate(raw):
    f = x["fields"]
    code = f.get("カレーグランプリ店舗コード", "").strip()
    sid = code if code and code not in seen_ids else f"x{i}"
    seen_ids.add(sid)
    score, page = find_page(x["name"], x["name_list"])
    if page is None: unmatched.append((x["name"], score, page))
    menu = [m.strip() for m in f.get("メインメニューおよびその他メニュー", "").split("\n") if m.strip()]
    # manual page overrides (fuzzy match failed)
    PAGE_FIX = {"喫茶 プペ": 30, "ハンバーグレストラン 牛舎本店": 33, "肆-YON-": 75, "オオドリー〈鴻〉神保町すずらん通り店": 49, "蕎麦ダイニング 煉 神田店": 51, "カレーショップ C&C 有楽町店": 56, "くずしわしょく香季庵 日本橋店": 59, "スパイス欧風カレーPAIKAJI": 63, "丼達": 69, "新潟カツ丼タレカツ神田今川橋店": 70, "スパイシービストロ タップロボーン 神保町店": 42, "スパイスカリー はちわん 神保町店": 64}
    if x["name"] in PAGE_FIX: page = PAGE_FIX[x["name"]]
    # clean description sections: cut at share/footer junk
    secs = []
    for sec in x.get("sections", []):
        if sec["h"] in ("共有:", "協賛企業", "特別協賛"): break
        p = sec["p"]
        for cut in ("取材日：", "取材日:", "*掲載内容は", "＊掲載内容は"):
            if cut in p: p = p[:p.index(cut)].strip()
        if sec["h"] or p: secs.append({"h": sec["h"], "p": p})
    x["sections"] = secs
    sns = {k: f[k] for k in ["Instagram", "Twitter", "Facebook", "blog"] if f.get(k)}
    web = f.get("ホームページ", "").strip()
    web = re.sub(r'\s.*$', '', web)
    out.append({
        "id": sid, "name": x["name"], "kana": f.get("てんめい", ""), "cat": int(x["cat_id"][1:]),
        "type": f.get("業態", ""), "addr": f.get("住所", "").strip(), "tel": f.get("電話番号", ""),
        "hours": f.get("営業時間", ""), "closed": f.get("定休日", ""), "menu": menu,
        "takeout": f.get("テイクアウト", ""), "seats": f.get("座席数", ""), "station": f.get("最寄駅", ""),
        "web": web, "sns": sns, "spice": f.get("辛さレベル", ""), "price": f.get("一人平均単価", ""),
        "halal": f.get("ハラール対応", ""), "kids": f.get("子供が食べられるカレー", ""), "allergy": f.get("アレルギー表記", ""),
        "lat": round(x["lat"], 6), "lng": round(x["lng"], 6), "approx": bool(x.get("approx")),
        "thumb": x.get("thumb"), "img": x.get("main_image"), "face": x.get("face_image"), "owner": x.get("owner_caption", ""),
        "desc": x.get("sections", []), "notice": x.get("notice", ""), "url": x["url"], "gmap": x.get("gmap_url"), "page": page,
        "sched": build_sched(f.get("営業時間", ""), f.get("定休日", "")),
        "pay": (OVERRIDES.get(sid, {}).get("pay") or extract_pay(x)),
        "paySrc": "報告" if OVERRIDES.get(sid, {}).get("pay") else ("公式" if extract_pay(x) else ""),
        "reserve": f.get("予約", ""), "quiet": f.get("比較的空いている時間", ""),
    })
print("unmatched pdf pages:", len(unmatched))
for u in unmatched: print("  ", u)
from collections import Counter
pc = Counter(o["page"] for o in out if o["page"])
print("pages with >3 stores:", {p: c for p, c in pc.items() if c > 3})
_ctrl = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
def _san(v):
    if isinstance(v, str): return _ctrl.sub('', v)
    if isinstance(v, list): return [_san(i) for i in v]
    if isinstance(v, dict): return {k: _san(i) for k, i in v.items()}
    return v
out = _san(out)
_nok = [o["name"] for o in out if not o["sched"]["ok"]]
print("hours parsed:", len(out) - len(_nok), "/", len(out), "| unparsed:", _nok)
print("pay known:", sum(1 for o in out if o["pay"]))
data = {"updated": datetime.date.today().isoformat(), "holidays": HOLIDAYS_2026, "source": "https://kanda-curry.com/stamprally2026/",
        "cats": {k: {"name": v[0], "color": v[1]} for k, v in CATS.items()}, "stores": out}
json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for p in sorted(pc):
    if pc[p] > 3: print("P%d:" % p, [o["name"] for o in out if o["page"] == p])
print("stores:", len(out), "size:", len(json.dumps(data, ensure_ascii=False)))
print(json.dumps(out[3], ensure_ascii=False, indent=1))

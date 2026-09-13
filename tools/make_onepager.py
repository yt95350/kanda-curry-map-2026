#!/usr/bin/env python3
"""一枚資料を生成する（Google Chrome のヘッドレス印刷を使用）
  docs/提案書_概要1枚.pdf  ← onepager.template.html（金額入り。返信後・打合せ用）
  docs/説明資料_1枚.pdf    ← about.template.html（金額なし。初回のフォーム連絡用。app/about.pdf にも複製）
"""
import json, os, subprocess, sys, base64, io, datetime, shutil, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs"); APP = os.path.join(HERE, "..", "app")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cfg = json.load(open(os.path.join(DOCS, "提案者情報.json"), encoding="utf-8"))
url = cfg.get("url") or "https://yt95350.github.io/kanda-curry-map-2026/full.html"

import qrcode
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=1)
qr.add_data(url); qr.make(fit=True)
img = qr.make_image(fill_color="#221C17", back_color="white").convert("1")
b = io.BytesIO(); img.save(b, format="PNG")
qr_uri = "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()

def ph(v, label): return v if v else f'<span class="ph">（{label}）</span>'
today = datetime.date.today()
vals = {
    "{{date}}": f"{today.year}年{today.month}月{today.day}日",
    "{{name}}": ph(cfg.get("name"), "お名前"),
    "{{org}}": f"（{cfg['org']}）" if cfg.get("org") else "",
    "{{email}}": ph(cfg.get("email"), "メールアドレス"),
    "{{tel_line}}": ("<br>" + cfg["tel"]) if cfg.get("tel") else "",
    "{{url_display}}": url.replace("https://", ""),
    "{{qr}}": qr_uri,
}

def build(template, out_pdf, out_html, copy_to=None):
    html = open(os.path.join(HERE, template), encoding="utf-8").read()
    for k, v in vals.items(): html = html.replace(k, v)
    tmpdir = tempfile.mkdtemp(prefix="onepager-")
    src = os.path.join(tmpdir, "page.html"); open(src, "w", encoding="utf-8").write(html)
    tmp_pdf = os.path.join(tmpdir, "out.pdf")
    proc = subprocess.Popen([CHROME, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                             f"--user-data-dir={tmpdir}/profile", "--virtual-time-budget=8000", "--no-pdf-header-footer",
                             f"--print-to-pdf={tmp_pdf}", "file://" + src], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 90; last = -1
    while time.time() < deadline:
        if os.path.exists(tmp_pdf):
            size = os.path.getsize(tmp_pdf)
            if size > 0 and size == last: break
            last = size
        if proc.poll() is not None and os.path.exists(tmp_pdf): break
        time.sleep(1)
    if proc.poll() is None: proc.terminate()
    if not os.path.exists(tmp_pdf): sys.exit(f"PDF が生成されませんでした: {template}")
    shutil.copy(tmp_pdf, os.path.join(DOCS, out_pdf))
    open(os.path.join(DOCS, out_html), "w", encoding="utf-8").write(html)
    if copy_to: shutil.copy(tmp_pdf, os.path.join(APP, copy_to))
    print("wrote", out_pdf, ("+ app/" + copy_to) if copy_to else "")

build("onepager.template.html", "提案書_概要1枚.pdf", "提案書_概要1枚.html")
build("about.template.html", "説明資料_1枚.pdf", "説明資料_1枚.html", copy_to="about.pdf")

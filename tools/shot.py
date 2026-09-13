#!/usr/bin/env python3
"""headless Chrome でスクリーンショットを撮る（Chrome が終了しない問題に対応して、ファイルができたら止める）"""
import os, subprocess, sys, tempfile, time
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
def shot(url, out, w, h, scale=2, budget=15000, extra=()):
    tmpdir = tempfile.mkdtemp(prefix="shot-")
    args = [CHROME, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
            f"--user-data-dir={tmpdir}/profile", f"--window-size={w},{h}", f"--force-device-scale-factor={scale}",
            f"--virtual-time-budget={budget}", f"--screenshot={out}", *extra, url]
    if os.path.exists(out): os.remove(out)
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 120; last = -1
    while time.time() < deadline:
        if os.path.exists(out):
            size = os.path.getsize(out)
            if size > 0 and size == last: break
            last = size
        if proc.poll() is not None and os.path.exists(out): break
        time.sleep(1)
    if proc.poll() is None: proc.terminate()
    if not os.path.exists(out): sys.exit("screenshot failed: " + url)
    return out
if __name__ == "__main__":
    url, out, w, h = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    scale = float(sys.argv[5]) if len(sys.argv) > 5 else 2
    print(shot(url, out, w, h, scale))

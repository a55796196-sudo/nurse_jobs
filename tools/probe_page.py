"""(임시) 게시판 표의 글 목록·상세를 읽어 로그로 출력."""
import re, sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto(URL, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2000)
    rows = pg.eval_on_selector_all("table tbody tr", "trs => trs.map(t => [t.innerText.replace(/\\s+/g,' ').trim(), (t.querySelector('a')||{}).href || ''])")
    print("NROWS", len(rows))
    for t, h in rows:
        print("ROW", t[:200], "|", h)
    for t, h in rows:
        m = re.search(r"(20\d\d-\d\d-\d\d)", t)
        if not h or "채용" not in t or (m and m.group(1) < "2026-11-01"):
            continue
        try:
            pg.goto(h, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(800)
            d = " ".join(pg.inner_text("body").split())
            k = d.find("제목"); print("\n####", t[:150], "\nURL", h, "\n", d[k:k+2500] if k >= 0 else d[:2500])
        except Exception as e:
            print("ERR", h, e)
    b.close()

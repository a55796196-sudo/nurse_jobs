"""(임시) 게시판 표에서 지정 번호 글을 눌러 상세 본문 출력."""
import re, sys
from playwright.sync_api import sync_playwright
URL, WANT = sys.argv[1], sys.argv[2].split(",")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for no in WANT:
        try:
            pg.goto(URL, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1500)
            row = pg.query_selector(f"table tbody tr:has(td:text-is('{no}'))")
            row.query_selector("a").click()
            pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1500)
            d = " ".join(pg.inner_text("body").split())
            k = d.find("공고번호"); print("\n####", no, pg.url, "\n", d[k:k+3500] if k >= 0 else d[:3500])
            print("FILES", pg.eval_on_selector_all("a", "els => els.map(e => e.innerText.trim()).filter(t => /\\.(hwp|hwpx|pdf)/i.test(t))"))
        except Exception as e:
            print("ERR", no, e)
    b.close()

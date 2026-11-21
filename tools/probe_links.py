"""(임시) 사이트에서 채용·구인 관련 링크와 목록 글자 출력."""
import re, sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for url in sys.argv[1:]:
        try:
            pg.goto(url, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1500)
            print("\nURL", url, "->", pg.url)
            links = pg.eval_on_selector_all("a", "els => els.map(e => [e.innerText.trim(), e.href])")
            for t, h in links:
                if re.search(r"구인|구직|채용|인재|Job|career|recruit|konect|cthub", t + h, re.I):
                    print("LINK", t[:50], "|", h)
            body = " ".join(pg.inner_text("body").split())
            print("BODY", body[:1500])
        except Exception as e:
            print("ERR", url, e)
    b.close()

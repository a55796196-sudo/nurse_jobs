from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page()
    for u in ("https://www.konect.or.kr/kr/board/recruit/boardList.do?pageIndex=1", "https://www.konect.or.kr/kr/board/recruit/boardList.do"):
        page.goto(u, wait_until="networkidle", timeout=60000); page.wait_for_timeout(1000)
        rows = page.eval_on_selector_all("table tbody tr", "trs => trs.map(t => [t.innerText.replace(/\\s+/g,' ').trim(), (t.querySelector('a')||{}).href || ''])")
        print("DBG", u, len(rows), rows[:3])
    b.close()
from src.sources import konect
print("FETCH", len(konect.fetch(days=120)))

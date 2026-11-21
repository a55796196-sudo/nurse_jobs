"""(임시) KoNECT 구인 게시판 목록·상세 구조."""
import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto(sys.argv[1], wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1500)
    rows = pg.eval_on_selector_all("table tbody tr, ul.board_list li, .bbs_list li", "els => els.map(t => [t.innerText.replace(/\\s+/g,' ').trim(), (t.querySelector('a')||{}).href || '', (t.querySelector('a')||{getAttribute:()=>''}).getAttribute('onclick')||''])")
    print("NROWS", len(rows))
    for r in rows[:25]: print("ROW", r[0][:160], "|", r[1], "|", r[2][:80])
    print("PAGER", [a for a in pg.eval_on_selector_all("a", "els => els.map(e => [e.innerText.trim(), e.href])") if 'page' in a[1].lower()][:6])
    if rows and rows[0][1]:
        pg.goto(rows[0][1], wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1000)
        print("DETAIL", pg.url, " ".join(pg.inner_text("body").split())[:2500])
        print("FILES", pg.eval_on_selector_all("a", "els => els.map(e => [e.innerText.trim(), e.href]).filter(x => /\\.(hwp|hwpx|pdf|docx)|down/i.test(x.join(' ')))"))
    b.close()

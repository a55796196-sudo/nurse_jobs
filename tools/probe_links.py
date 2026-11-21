from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page()
    r = page.goto("https://www.konect.or.kr/kr/board/recruit/boardList.do", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2500)
    print("DBG status", r.status if r else None, page.url)
    print("DBG body", " ".join(page.inner_text("body").split())[:1200])
    print("DBG tables", page.eval_on_selector_all("table", "ts => ts.map(t => t.innerText.slice(0,200))"))
    b.close()

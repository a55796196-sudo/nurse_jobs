from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
urls = ["https://www.work24.go.kr/wk/a/b/1500/empDetailAuthView.do?wantedAuthNo=51974659&infoTypeCd=CJK&infoTypeGroup=tb_workinfogubun",
        "https://www.work24.go.kr/wk/a/b/1500/empDetailAuthView.do?wantedAuthNo=55608183&infoTypeCd=CSI&infoTypeGroup=tb_workinfogubun"]
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(user_agent=UA, locale="ko-KR"); pg = ctx.new_page()
    for u in urls:
        pg.goto(u, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(1500)
        els = pg.query_selector_all("a:has-text('채용사이트'), a:has-text('바로가기'), button:has-text('채용사이트')")
        for e in els:
            print("LINK", (e.inner_text() or "").strip()[:20], "|", e.get_attribute("href"), "|", (e.get_attribute("onclick") or "")[:200])
        try:
            with ctx.expect_page(timeout=15000) as np:
                pg.click("text=채용사이트 바로가기", timeout=5000)
            newp = np.value; newp.wait_for_load_state("domcontentloaded", timeout=30000)
            print("OPENED", newp.url)
            t = " ".join(newp.inner_text("body").split())
            for kw in ("자격", "간호", "보건관리자", "우대", "급여", "근무"):
                i = t.find(kw)
                if i >= 0: print("TXT", kw, "::", t[max(0,i-60):i+260])
            newp.close()
        except Exception as e:
            print("ERR", e)
    b.close()

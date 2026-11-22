from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for k in range(3):
        try:
            r = pg.goto("https://www.korea.kr/archive/recruitInfoView.do?dataId=400228", wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(2000)
            t = " ".join(pg.inner_text("body").split()); i = t.find("고양시")
            print("CHK", r.status if r else None, t[i:i+200]); break
        except Exception as e:
            print("ERR", e); pg.wait_for_timeout(8000)
    b.close()

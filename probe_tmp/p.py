from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    pg.goto("https://job.incruit.com/jobdb_info/jobpost.asp?job=2611240001984", wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(6000)
    for f in pg.frames:
        if "jobpostcont" in f.url:
            print("CONT", " ".join(f.inner_text("body").split())[:6000])
            for im in f.eval_on_selector_all("img", "is=>is.map(i=>[i.src,i.naturalWidth,i.naturalHeight])"): print("IMG", im)
    b.close()

from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    pg.goto("https://job.incruit.com/jobdb_info/jobpost.asp?job=2610270004575", wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(5000)
    for f in pg.frames:
        try:
            t=" ".join(f.inner_text("body").split())
            if "jobpostcont" in f.url or f == pg.main_frame: print("FT", f.url[:70], t[:5000])
        except Exception as e: print(e)
    for im in pg.frames[1].eval_on_selector_all("img", "is=>is.map(i=>[i.src,i.naturalWidth,i.naturalHeight])") if len(pg.frames)>1 else []:
        print("IMG", im)
    b.close()

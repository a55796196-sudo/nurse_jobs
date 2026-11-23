import re
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    pg.goto("https://search.incruit.com/list/search.asp?col=job&kw=CRC", wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(4000)
    h = pg.content(); i = h.find("2611180001031")
    print("ROWHTML", h[max(0,i-2500):i+3000].replace("\n"," "))
    print("URL", pg.url)
    for u in ["https://job.incruit.com/jobdb_info/jobpost.asp?job=2611180001031", "https://job.incruit.com/jobdb_info/jobpost.asp?job=2611140000285"]:
        pg.goto(u, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(4000)
        print("FRAMES", [f.url for f in pg.frames])
        for f in pg.frames:
            try: print("FTEXT", f.url[:80], " ".join(f.inner_text("body").split())[:3500])
            except Exception as e: print("ferr", e)
    b.close()

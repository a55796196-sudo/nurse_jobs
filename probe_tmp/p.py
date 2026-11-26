import json
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
IDS = ["99763","100785","99828","99764","99572","99187","100788","100771"]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for sid in IDS:
        got = {}
        h = lambda r, sid=sid, got=got: got.update(r.json().get("data") or {}) if r.url.split("?")[0].endswith(f"/job_posting/{sid}") else None
        pg.on("response", h)
        pg.goto(f"https://www.nursevillage.com/job/job-posting/{sid}", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1500)
        pg.remove_listener("response", h)
        print("URLS", sid, got.get("orgNameRaw"), "|", got.get("replaceUrl"), "|", got.get("sourceUrl"), "|", got.get("sourceSite"), "|", got.get("endDate"))
    b.close()

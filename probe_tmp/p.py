import json
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
js = json.load(open("data/jobs/2026-11-22.json"))
urls = {j["source_id"]: j["url"] for j in js if j["source"] == "work24" and j.get("blog_pick")}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for k, u in urls.items():
        pg.goto(u, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(1500)
        t = " ".join(pg.inner_text("body").split())
        i = t.find("모집요강")
        print("DET", k, "::", t[i:i+2600])
    b.close()

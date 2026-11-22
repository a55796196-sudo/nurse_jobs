import json, re, html as H
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
js = json.load(open("data/jobs/2026-11-22.json"))
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for j in js:
        if j["source"] != "work24" or not j.get("blog_pick"):
            continue
        d = j["extra"]["detail_url"]
        pg.goto(d, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(1500)
        t = " ".join(pg.inner_text("body").split()); i = t.find("모집요강")
        rec = {"detail": t[i:i+5000]}
        m = re.search(r"f_goMove\('([^']+)'\)", pg.content())
        if m:
            try:
                pg.goto(H.unescape(m.group(1)), wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(4000)
                o = " ".join(pg.inner_text("body").split()); k = o.find("모집요강")
                rec["origin"] = o[k if k > 0 else 0:][:7000]
            except Exception as e:
                rec["origin_err"] = str(e)[:200]
        out[j["source_id"]] = rec
    b.close()
print("JSONOUT" + json.dumps(out, ensure_ascii=False))

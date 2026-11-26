import json
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(user_agent=UA, locale="ko-KR"); pg = ctx.new_page()
    apis = []
    def on_resp(r):
        if "api-v2.nursevillage.com/job_posting" in r.url:
            try: apis.append((r.url, r.text()[:3000]))
            except Exception: pass
    pg.on("response", on_resp)
    for sid in ("99763", "99572", "100785"):
        apis.clear()
        pg.goto(f"https://www.nursevillage.com/job/job-posting/{sid}", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2000)
        print("##", sid)
        for u, t in apis: print("  API", u[:120]); print("   ", t[:1500])
        els = pg.eval_on_selector_all("a,button", "as=>as.filter(a=>/공고 보러가기|원문/.test(a.innerText)).map(a=>[a.tagName,a.innerText.trim(),a.getAttribute('href'),a.outerHTML.slice(0,300)])")
        print("  ELS", els)
        try:
            with ctx.expect_page(timeout=8000) as np:
                pg.get_by_text("공고 보러가기").first.click()
            newp = np.value; newp.wait_for_load_state("domcontentloaded", timeout=20000); print("  POPUP", newp.url); newp.close()
        except Exception as e:
            print("  no popup", str(e)[:80], "| now", pg.url)
    b.close()

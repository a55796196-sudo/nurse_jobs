import json
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for gid in ("50389774", "50395495"):
        pg.goto(f"https://www.jobkorea.co.kr/Recruit/GI_Read/{gid}", wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(6000)
        texts = []
        for fr in pg.frames:
            try:
                t = " ".join(fr.inner_text("body").split())
                texts.append((fr.url[:120], t[:6000]))
            except Exception:
                pass
        imgs = []
        for fr in pg.frames:
            try:
                imgs += fr.eval_on_selector_all("img", "els => els.filter(e => e.naturalWidth > 500).map(e => e.src)")
            except Exception:
                pass
        out[gid] = {"frames": texts, "imgs": imgs[:10]}
    b.close()
print("JSONOUT" + json.dumps(out, ensure_ascii=False))

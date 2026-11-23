import re, os
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
os.makedirs("probe_out", exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(user_agent=UA, locale="ko-KR", accept_downloads=True); pg = ctx.new_page()
    for u in ["https://jobapplication.schmc.ac.kr/recruit/biz/job/recruitedetail", "https://jobapplication.schmc.ac.kr/"]:
        try:
            pg.goto(u, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(3000)
            print("### URL", u, "->", pg.url, pg.title())
            print("TEXT", " ".join(pg.inner_text("body").split())[:2500])
            for l in pg.eval_on_selector_all("a,button,li[onclick],tr[onclick],div[onclick]", "as=>as.map(a=>[a.innerText.trim().replace(/\\s+/g,' ').slice(0,60),a.getAttribute('href'),a.getAttribute('onclick')])"):
                if l[0] and (re.search(r"임상|연구|간호|채용|공고|recruit", " ".join(map(str,l)))): print("  L", l)
        except Exception as e: print("ERR", u, e)
    # 임상시험 공고 클릭 시도
    try:
        el = pg.locator("text=/임상시험/").first
        el.click(timeout=15000); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(3000)
        print("### CLICKED ->", pg.url)
        print("DETAIL", " ".join(pg.inner_text("body").split())[:6000])
        for l in pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().slice(0,60),a.getAttribute('href'),a.getAttribute('onclick')])"):
            if re.search(r"down|file|첨부|\.pdf|\.hwp", " ".join(map(str,l)), re.I): print("  F", l)
        pg.screenshot(path="probe_out/detail.png", full_page=True)
        for im in pg.eval_on_selector_all("img", "is=>is.map(i=>[i.src,i.naturalWidth,i.naturalHeight])"):
            if im[1] and im[1] > 400: print("  IMG", im)
    except Exception as e: print("CLICK ERR", e)
    b.close()

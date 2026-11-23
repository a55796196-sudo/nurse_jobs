import re, time
from urllib.parse import quote
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SITES = {
 "jobkorea": "https://www.jobkorea.co.kr/Search/?stext={q}&tabType=recruit",
 "saramin": "https://www.saramin.co.kr/zf_user/search/recruit?searchword={q}&recruitSort=reg_dt",
 "wanted": "https://www.wanted.co.kr/search?query={q}&tab=position",
 "incruit": "https://search.incruit.com/list/search.asp?col=job&kw={q}",
}
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(user_agent=UA, locale="ko-KR")
    for name, u in SITES.items():
        for q in ("CRC", "연구간호사", "CRA", "보건관리자"):
            pg = ctx.new_page()
            try:
                pg.goto(u.format(q=quote(q)), wait_until="domcontentloaded", timeout=45000); pg.wait_for_timeout(5000)
                links = pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().replace(/\\s+/g,' ').slice(0,70),a.href])")
                pat = {"jobkorea": r"/Recruit/GI_Read/", "saramin": r"rec_idx=|recruit-view", "wanted": r"/wd/\d+", "incruit": r"jobdb_info|jobpost"}[name]
                hits = [l for l in links if re.search(pat, l[1]) and len(l[0]) > 5]
                seen=set(); hits=[h for h in hits if not (h[1] in seen or seen.add(h[1]))]
                print(f"## {name} {q}: {len(hits)}건  ({pg.title()[:40]})")
                for h in hits[:8]: print("    ", h[0], "|", h[1][:90])
            except Exception as e:
                print(f"## {name} {q}: ERR {str(e)[:120]}")
            pg.close(); time.sleep(2)
    b.close()

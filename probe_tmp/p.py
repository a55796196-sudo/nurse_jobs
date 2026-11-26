import re, json
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(user_agent=UA, locale="ko-KR")
    pg = ctx.new_page()
    api = []
    pg.on("response", lambda r: api.append(r.url) if ("api" in r.url or "json" in (r.headers.get("content-type") or "")) else None)
    pg.goto("https://www.nursevillage.com/job/job-posting", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2000)
    for _ in range(6):
        pg.mouse.wheel(0, 20000); pg.wait_for_timeout(1500)
    ls=[l for l in pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().replace(/\\s+/g,' ').slice(0,90),a.href])") if re.search(r'/job-posting/\d+', l[1])]
    print("NV after scroll", len(ls))
    for l in ls:
        if re.search(r"보험심사|연구|CRC|보건관리|산업간호|QI|적정|감염관리|보건교사|보건실|임상시험|코디", l[0]): print("   HIT", l[0][:90], l[1][:60])
    print("NV api", sorted(set(u.split('?')[0] for u in api))[:15])
    # 기업·기관 탭 클릭
    try:
        pg.get_by_text("기업·기관").first.click(); pg.wait_for_timeout(3000)
        ls2=[l for l in pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().replace(/\\s+/g,' ').slice(0,90),a.href])") if re.search(r'/job-posting/\d+', l[1])]
        print("NV 기업기관", len(ls2)); [print("   ", l[0][:90]) for l in ls2[:15]]
    except Exception as e: print("NV tab err", e)
    pg.goto("https://www.kaohn.or.kr/board/bbs81_1", wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(2500)
    print("KAOHN 구인구직", " ".join(pg.inner_text("body").split())[:2500])
    rows=[l for l in pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().slice(0,70),a.href])") if '/board/bbs81_1/' in l[1]]
    print("KAOHN rows", rows[:10])
    if rows:
        pg.goto(rows[0][1], wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(2000)
        print("KAOHN detail", " ".join(pg.inner_text("body").split())[:1500])
    b.close()

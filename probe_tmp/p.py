import re
from urllib.parse import quote
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(user_agent=UA, locale="ko-KR")
    pg = ctx.new_page()
    pg.goto("https://www.nursevillage.com/job/job-posting", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(3000)
    print("NV tabs", [l for l in pg.eval_on_selector_all("a,button", "as=>as.map(a=>[a.innerText.trim().slice(0,20),a.getAttribute('href')])") if l[0] and len(l[0])<15][:60])
    print("NV body", " ".join(pg.inner_text("body").split())[:1500])
    for q in ["tab=company", "tab=public", "tab=hospital&page=2&sort=latest", "keyword="+quote("보건관리자")]:
        try:
            pg.goto("https://www.nursevillage.com/job/job-posting?"+q, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2500)
            ls=[l for l in pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().replace(/\\s+/g,' ').slice(0,90),a.href])") if '/job-posting/' in l[1]]
            print("## NV", q, len(ls)); [print("   ", l[0]) for l in ls[:6]]
        except Exception as e: print("NV ERR", q, e)
    pg.goto("https://www.nursevillage.com/job/job-posting/99763", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(3000)
    print("NV DETAIL", " ".join(pg.inner_text("body").split())[:3000])
    for u in ["https://www.peoplenjob.com/jobs?keyword="+quote("CRA"), "https://www.peoplenjob.com/jobs?search_keyword="+quote("CRA")]:
        pg.goto(u, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(3000)
        ls=[l for l in pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().replace(/\\s+/g,' ').slice(0,80),a.href])") if re.search(r'CRA|임상|Clinical|간호|Nurse', l[0], re.I)]
        print("## PNJ", u, len(ls)); [print("   ", l) for l in ls[:6]]
    forms = pg.eval_on_selector_all("form", "fs=>fs.map(f=>[f.action,[...f.querySelectorAll('input')].map(i=>i.name)])"); print("PNJ forms", forms[:4])
    pg.goto("https://www.kaohn.or.kr/", wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(2000)
    print("KAOHN", [l for l in pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().slice(0,30),a.href])") if re.search(r'구인|구직|채용|취업', l[0])][:10])
    try:
        pg.goto("https://job.cleaneye.go.kr/", wait_until="domcontentloaded", timeout=90000); pg.wait_for_timeout(3000)
        print("CLEANEYE", pg.url, " ".join(pg.inner_text("body").split())[:500])
    except Exception as e: print("CLEANEYE ERR", e)
    b.close()

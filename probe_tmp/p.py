import re
from urllib.parse import quote
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
K = re.compile(r"보건관리|산업간호|CRC|CRA|연구간호|임상연구|임상시험|보험심사|심사간호|보건교사|보건실|보건소|간호사", re.I)
URLS = [
 ("널스빌리지", "https://www.nursevillage.com/job/job-posting"),
 ("널스잡", "https://www.nursejob.co.kr/"),
 ("하이브레인넷 간호", "https://www.hibrain.net/recruitment/search?keyword="+quote("간호")),
 ("하이브레인넷 보건", "https://www.hibrain.net/recruitment/search?keyword="+quote("보건실")),
 ("피플앤잡 CRA", "https://www.peoplenjob.com/jobs?q="+quote("CRA")),
 ("클린아이 잡플러스", "https://job.cleaneye.go.kr/"),
 ("산업간호협회", "https://www.kaohn.or.kr/"),
 ("대한간호협회", "https://www.koreanurse.or.kr/"),
 ("인디드 보건관리자", "https://kr.indeed.com/jobs?q="+quote("보건관리자")),
 ("잡플래닛 보건관리자", "https://www.jobplanet.co.kr/job/search?q="+quote("보건관리자")),
 ("메디잡", "https://www.medijob.cc/"),
]
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(user_agent=UA, locale="ko-KR")
    for name, u in URLS:
        pg = ctx.new_page()
        try:
            r = pg.goto(u, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(4000)
            links = pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().replace(/\\s+/g,' ').slice(0,70),a.href])")
            hits = [l for l in links if K.search(l[0]) and len(l[0]) > 6]
            seen=set(); hits=[h for h in hits if not (h[1] in seen or seen.add(h[1]))]
            print(f"## {name} status={r.status if r else '?'} final={pg.url[:80]} title={pg.title()[:40]} links={len(links)} hits={len(hits)}")
            for h in hits[:6]: print("    ", h[0], "|", h[1][:100])
            if not hits: print("    TEXT", " ".join(pg.inner_text("body").split())[:300])
        except Exception as e:
            print(f"## {name} ERR {str(e)[:140]}")
        pg.close()
    b.close()

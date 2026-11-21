import re, sys
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
urls = [
 "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?srcKeyword=%EB%B3%B4%EA%B1%B4%EA%B4%80%EB%A6%AC%EC%9E%90",
 "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do",
]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for u in urls:
        try:
            pg.goto(u, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(3000)
            body = " ".join(pg.inner_text("body").split())
            print("\nURL", u, "->", pg.url, len(body))
            i = body.find("보건관리자"); print("BODY", body[max(0,i-300):i+2500] if i >= 0 else body[:2500])
            print("INPUTS", pg.eval_on_selector_all("input[type=text],input:not([type])", "els => els.map(e => [e.name, e.id, e.title, e.placeholder])")[:15])
            links = pg.eval_on_selector_all("a", "els => els.map(e => [e.innerText.trim().slice(0,60), e.href, (e.getAttribute('onclick')||'').slice(0,80)])")
            print("LINKS", [l for l in links if re.search(r"wantedAuthNo|empDetail|Detail|보건|간호", ' '.join(l))][:15])
        except Exception as e:
            print("ERR", u, e)
    b.close()

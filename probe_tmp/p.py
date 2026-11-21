import re
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
u = "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?srcKeyword=%EB%B3%B4%EA%B1%B4%EA%B4%80%EB%A6%AC%EC%9E%90"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    pg.goto(u, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(2000)
    h = pg.content()
    print("NAMES", sorted(set(re.findall(r'name="([A-Za-z_]+)"', h)))[:120])
    i = h.find("다온티앤티") if "다온티앤티" in h else h.find("D-")
    m = re.search(r"<tr[^>]*>(?:(?!</tr>).)*?wantedAuthNo(?:(?!</tr>).)*</tr>", h, re.S)
    print("ROWHTML", (m.group(0) if m else h[i-3000:i+1500])[:4000])
    print("AUTH", re.findall(r"wantedAuthNo=([A-Za-z0-9]+)[^\"']*", h)[:5])
    print("HREFS", re.findall(r'href="([^"]*(?:Detail|detail)[^"]*)"', h)[:5])
    b.close()

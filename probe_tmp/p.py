import re, html as H
from urllib.parse import quote
from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for kw in ("보건관리자", "대한산업보건협회 간호사"):
        pg.goto(f"https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?srcKeyword={quote(kw)}&keywordWantedTitle=Y&pageIndex=1&sortField=DATE&sortOrderBy=DESC", wait_until="networkidle", timeout=90000)
        pg.wait_for_timeout(1500)
        h = pg.content()
        for m in re.finditer(r'<a[^>]*(?:href|onclick)="([^"]*wantedAuthNo=([A-Za-z0-9]+)[^"]*)"', h):
            print("HREF", m.group(2), H.unescape(m.group(1))[:250])
        for m in re.finditer(r'onclick="([^"]*(?:55608183|51969656|51974659)[^"]*)"', h):
            print("ONCLICK", H.unescape(m.group(1))[:250])
    for u in ("https://www.work24.go.kr/wk/a/b/1500/empDetailAuthView.do?wantedAuthNo=51969656&infoTypeCd=VALIDATION&infoTypeGroup=tb_workinfoworknet",):
        pg.goto(u, wait_until="networkidle", timeout=90000); print("DETAILURL", pg.url, " ".join(pg.inner_text("body").split())[:300])
    b.close()

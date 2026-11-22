from playwright.sync_api import sync_playwright
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
urls = {
 "55608183": "https://www.work24.go.kr/wk/a/b/1500/empDetailAuthView.do?wantedAuthNo=55608183&infoTypeCd=CSI&infoTypeGroup=tb_workinfogubun",
 "51969656": "https://www.work24.go.kr/wk/a/b/1500/empDetailAuthView.do?wantedAuthNo=51969656&infoTypeCd=CJK&infoTypeGroup=tb_workinfogubun",
 "51974659": "https://www.work24.go.kr/wk/a/b/1500/empDetailAuthView.do?wantedAuthNo=51974659&infoTypeCd=CJK&infoTypeGroup=tb_workinfogubun",
}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for k, u in urls.items():
        pg.goto(u, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(1500)
        t = " ".join(pg.inner_text("body").split())
        i = max(t.find("보건"), 0)
        print("CHK", k, pg.url[-60:], "|", t[i:i+400])
    b.close()

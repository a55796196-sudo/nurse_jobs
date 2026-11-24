from playwright.sync_api import sync_playwright
from src.sources.work24 import UA
U="https://www.work24.go.kr/wk/a/b/1500/empDetailAuthView.do?wantedAuthNo=K172112611230068&infoTypeCd=VALIDATION&infoTypeGroup=tb_workinfoworknet"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for k in range(3):
        try:
            pg.goto(U, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(2000)
            t=" ".join(pg.inner_text("body").split()); i=t.find("무기계약직 보건관리자")
            print("BODY", t[i:i+7000]); break
        except Exception as e: print("ERR", e)
    b.close()

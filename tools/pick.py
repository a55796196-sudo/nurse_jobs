"""일회성: 후보 공고 상세 읽기."""
from playwright.sync_api import sync_playwright
URLS = [
    "https://work.sen.go.kr/work/search/recInfo/BD_selectRecDetail.do?q_rcrtSn=110520",
    "https://nmc.recruiter.co.kr/app/jobnotice/view?systemKindCode=MRS2&jobnoticeSn=271567",
]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for url in URLS:
        try:
            pg.goto(url, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2500)
        except Exception as e:
            print("###", url, "실패", e); continue
        texts = []
        for fr in pg.frames:
            try: texts.append(" ".join(fr.inner_text("body", timeout=10000).split()))
            except Exception: pass
        print(f"\n### {url}\n" + "\n".join(texts)[:7000])
    b.close()

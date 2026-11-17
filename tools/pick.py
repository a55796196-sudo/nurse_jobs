"""일회성: 시도교육청 구인 게시판에서 보건교사 공고 찾기."""
import re
from playwright.sync_api import sync_playwright
SITES = {
    "서울": "https://work.sen.go.kr/work/search/recInfo/BD_selectSrchRecInfo.do",
    "경기": "https://www.goe.go.kr/recruit/main.do",
}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for name, url in SITES.items():
        try:
            pg.goto(url, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2000)
        except Exception as e:
            print("###", name, "접속 실패", e); continue
        print(f"\n### {name} {pg.url} / {pg.title()}")
        # 검색창이 있으면 '보건' 검색
        for sel in ("input[name*='earch']", "input[name*='keyword']", "input[type='search']", "input[title*='검색']", "input[name='srchKwd']"):
            try:
                el = pg.query_selector(sel)
                if el and el.is_visible():
                    el.fill("보건"); el.press("Enter"); pg.wait_for_timeout(3000)
                    print("검색 실행:", sel); break
            except Exception:
                pass
        text = pg.inner_text("body")
        lines = [l.strip() for l in text.split("\n") if "보건" in l]
        print("보건 포함 줄:", lines[:30])
        links = pg.eval_on_selector_all("a", "els => els.map(e => [e.innerText.trim().slice(0,120), e.href, e.getAttribute('onclick')]).filter(x => x[0].includes('보건'))")
        print("보건 링크:", links[:20])
        print("페이지 일부:", " ".join(text.split())[:1500])
    b.close()

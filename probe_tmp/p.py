import re, time
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from src.sources.work24 import LIST, UA, _rows
KW = ["CRC","CRA","임상연구","임상시험","연구간호사","임상연구코디네이터","임상시험코디네이터","모니터요원","SMO","CRO","연구코디네이터","임상연구간호사","의료기기 임상","임상 간호사 연구"]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(user_agent=UA, locale="ko-KR").new_page()
    for kw in KW:
        for t in ("Y","N"):
            url=f"{LIST}?srcKeyword={quote(kw)}&keywordWantedTitle={t}&keywordFlag=&pageIndex=1&sortField=DATE&sortOrderBy=DESC"
            try:
                pg.goto(url, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(1500)
                rows=_rows(pg.content())
                tot=re.search(r"총\s*([\d,]+)\s*건", pg.inner_text("body"))
                print(f"## {kw} title={t} total={tot.group(1) if tot else '?'} rows={len(rows)}")
                for r in rows[:10]: print("   ", r["posted"], r["deadline"], r["title"][:60])
            except Exception as e: print(kw,t,"ERR",e)
            time.sleep(2)
    # KoNECT
    for u in ["https://www.konect.or.kr/kr/board/recruit/boardList.do","https://www.konect.or.kr/kr/contents/recruit/view.do","https://www.konect.or.kr/kr/index.do"]:
        try:
            pg.goto(u, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(4000)
            print("### KONECT", u, "->", pg.url)
            links = pg.eval_on_selector_all("a", "as=>as.map(a=>[a.innerText.trim().slice(0,30),a.getAttribute('href'),a.getAttribute('onclick')])")
            for l in links:
                s=" ".join(map(str,l))
                if re.search(r"구인|recruit|인력|채용|board", s, re.I): print("   ", l)
            print("   FRAMES", [f.url for f in pg.frames])
        except Exception as e: print("konect", u, e)
    b.close()

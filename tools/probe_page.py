"""(임시) 게시판 목록·상세 글을 읽어 로그로 출력."""
import re, sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto(URL, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2000)
    body = " ".join(pg.inner_text("body").split())
    i = body.find("번호"); print("LIST", body[i:i+4000] if i > 0 else body[:4000])
    links = pg.eval_on_selector_all("a", "els => els.map(e => [e.innerText.trim(), e.href, e.getAttribute('onclick')||''])")
    rows = [l for l in links if re.search(r"간호|보건|건강|치매|정신|방문|감염|예방접종|모자|결핵|암", l[0]) and len(l[0]) > 8]
    print("ROWS", len(rows))
    for t, h, oc in rows[:25]:
        print("ROW", t[:90], "|", h, "|", oc[:80])
    for t, h, oc in rows[:15]:
        if not h.startswith("http") or "javascript" in h:
            continue
        try:
            pg.goto(h, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1000)
            d = " ".join(pg.inner_text("body").split())
            k = d.find(t[:15]); print("\n#### ", t[:90], "\n", d[k:k+1800] if k >= 0 else d[:1800])
        except Exception as e:
            print("ERR", h, e)
    b.close()

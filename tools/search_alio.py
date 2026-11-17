"""일회성: 한국의료기기안전정보원 공고 상세 + 채용사이트 본문."""
import json, os, re, requests
from playwright.sync_api import sync_playwright
KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
det = {}
for base in ("https://apis.data.go.kr", "http://apis.data.go.kr") * 2:
    try:
        det = requests.get(base + "/1051000/recruitment/detail",
                           params={"serviceKey": KEY, "resultType": "json", "sn": 306748}, timeout=60).json().get("result") or {}
        break
    except Exception as e:
        print("API 재시도", e.__class__.__name__)
print("첨부:", [f.get("atchFileNm") for f in det.get("files") or []])
print("단계:", [s.get("recrutPbancTtl") for s in det.get("steps") or []])
for k in ("aplyQlfcCn", "prefCondCn", "scrnprcdrMthdExpln", "disqlfcRsn", "nonatchRsn"):
    print(k, ":", " ".join(str(det.get(k) or "").split())[:1500])
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto("https://dware.intojob.co.kr/main/nids.jsp", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2000)
    print("\n사이트 목록:", " ".join(pg.inner_text("body").split())[:1500])
    links = pg.eval_on_selector_all("a", "els => els.map(e => [e.innerText.trim().slice(0,80), e.href, e.getAttribute('onclick')])")
    cand = [l for l in links if re.search(r"제5차|기간제|채용", l[0] or "")][:5]
    print("링크 후보:", cand)
    for t, href, onclick in cand[:2]:
        try:
            if href and href.startswith("http") and "#" not in href:
                pg.goto(href, wait_until="networkidle", timeout=60000)
            else:
                pg.click(f"text={t[:20]}", timeout=10000); pg.wait_for_timeout(3000)
            texts = []
            for fr in pg.frames:
                try: texts.append(" ".join(fr.inner_text("body").split()))
                except Exception: pass
            print("\n상세:", pg.url, "\n", "\n".join(texts)[:5000])
            imgs = pg.eval_on_selector_all("img", "els => els.map(e => [e.src, e.naturalWidth]).filter(x => x[1] > 500)")
            print("이미지:", imgs[:6])
        except Exception as e:
            print("상세 실패", t, e)
    b.close()

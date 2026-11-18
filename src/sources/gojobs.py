"""나라일터(gojobs.go.kr)에서 보건소·치매안심센터 등 지자체 간호 공고 수집.

검색창에 키워드를 넣어 목록을 읽고, 상세 페이지(apmView.do?empmnsn=번호) 본문을 저장한다.
GitHub Actions(국내 사이트 접속 가능)에서만 동작한다. Playwright 필요.
"""
from __future__ import annotations

import re

from ..models import Job

LIST = "https://www.gojobs.go.kr/apmList.do"
KEYWORDS = ["보건소 간호", "치매안심센터", "방문간호", "정신건강복지센터 간호", "보건지소"]
NURSE = re.compile(r"간호")


def _text_all(page) -> str:
    out = []
    for fr in page.frames:
        try:
            out.append(" ".join(fr.inner_text("body", timeout=10000).split()))
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(out)


def _search(page, kw: str) -> list[tuple[str, str]]:
    page.goto(LIST, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    box = None
    for sel in ("input[name='searchKwd']", "input[name*='earch'][type='text']", "input[title*='검색']", "input[type='text']"):
        el = page.query_selector(sel)
        if el and el.is_visible():
            box = el
            break
    if not box:
        print("[gojobs] 검색창 없음")
        return []
    box.fill(kw)
    box.press("Enter")
    page.wait_for_timeout(3000)
    links = page.eval_on_selector_all(
        "a", "els => els.map(e => [e.innerText.trim(), e.href, e.getAttribute('onclick') || ''])")
    out = []
    for t, h, oc in links:
        m = re.search(r"empmnsn=(\d+)", h or "") or re.search(r"(\d{5,})", oc or "")
        if m and t:
            out.append((" ".join(t.split()), f"https://www.gojobs.go.kr/apmView.do?empmnsn={m.group(1)}"))
    return out


def fetch(max_per_kw: int = 15) -> list[Job]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[gojobs] playwright 없음 → 건너뜀")
        return []
    found: dict[str, Job] = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        for kw in KEYWORDS:
            try:
                items = _search(page, kw)
            except Exception as e:  # noqa: BLE001
                print(f"[gojobs] 검색 실패 {kw}: {e}")
                continue
            for title, url in items[:max_per_kw]:
                sid = url.split("=")[-1]
                if sid in found:
                    continue
                try:
                    page.goto(url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(1500)
                    body = _text_all(page)
                except Exception as e:  # noqa: BLE001
                    print(f"[gojobs] 상세 실패 {url}: {e}")
                    continue
                if not NURSE.search(title + " " + body[:4000]):
                    continue
                m_org = re.search(r"(?:기관명|채용기관)\s*[:：]?\s*(\S+(?:\s\S+)?(?:시|군|구|도|보건소|청))", body)
                m_dl = re.search(r"(?:접수기간|공고기간|원서접수)\D{0,20}(20\d\d)[.\-](\d{1,2})[.\-](\d{1,2})\D{1,30}(20\d\d)[.\-](\d{1,2})[.\-](\d{1,2})", body)
                dl = f"{m_dl.group(4)}-{int(m_dl.group(5)):02d}-{int(m_dl.group(6)):02d}" if m_dl else None
                st = f"{m_dl.group(1)}-{int(m_dl.group(2)):02d}-{int(m_dl.group(3)):02d}" if m_dl else None
                m_loc = re.search(r"(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)\S*\s*(\S+[시군구])?", m_org.group(1) if m_org else title + " " + body[:500])
                found[sid] = Job(
                    source="gojobs", source_id=sid, title=title[:120], url=url,
                    org=m_org.group(1) if m_org else "지자체",
                    deadline=dl, start_date=st,
                    location=" ".join(x for x in (m_loc.groups() if m_loc else []) if x) or None,
                    employment_type="기간제" if "기간제" in title + body[:2000] else None,
                    raw_text=(title + " " + body)[:3000],
                    extra={"site_text": body[:8000], "detail_url": url, "search_kw": kw},
                )
        b.close()
    print(f"[gojobs] 간호 관련 {len(found)}건")
    return list(found.values())

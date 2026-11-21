"""KoNECT(국가임상시험지원재단) '관련기관 인력 구인' 게시판 — 병원·SMO·CRO 의 CRC·CRA·연구간호사 공고.

GitHub Actions(국내 사이트 접속 가능)에서만 동작한다. Playwright 필요.
"""
from __future__ import annotations

import datetime as dt
import re

from ..models import Job

LIST = "https://www.konect.or.kr/kr/board/recruit/boardList.do"
WANT = re.compile(r"CRC|CRA|연구간호|임상연구|임상시험|코디네이터|간호", re.I)
DATE = re.compile(r"(20\d\d)[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})")


def _d(m) -> str:
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def fetch(days: int = 45, pages: int = 2) -> list[Job]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[konect] playwright 없음 → 건너뜀")
        return []
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    jobs: list[Job] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                             locale="ko-KR").new_page()
        rows = []
        for n in range(1, pages + 1):
            try:
                for k in range(3):   # 본문 표가 늦게 뜨거나 안 뜨는 경우가 있어 몇 번 다시 염
                    page.goto(f"{LIST}?pageIndex={n}", wait_until="networkidle", timeout=60000)
                    try:
                        page.wait_for_selector("a[href*='boardView.do?bbsIdx']", timeout=20000)
                        break
                    except Exception:  # noqa: BLE001
                        page.wait_for_timeout(5000 * (k + 1))
                page.wait_for_timeout(500)
                rows += page.eval_on_selector_all(
                    "tr:has(a[href*='boardView.do?bbsIdx'])",
                    "trs => trs.map(t => [t.innerText.replace(/\\s+/g,' ').trim(), (t.querySelector('a')||{}).href || ''])")
            except Exception as e:  # noqa: BLE001
                print(f"[konect] 목록 실패 p{n}: {e}")
                break
        for text, href in rows:
            m = re.search(r"(\d\d)\.(\d\d)\.(\d\d)\s+\d+\s*$", text)   # 작성일 26.11.19 + 조회수
            posted = f"20{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
            sid = re.search(r"bbsIdx=(\d+)", href or "")
            if not sid or not WANT.search(text) or (posted and posted < since):
                continue
            title = re.sub(r"^\d+\s+", "", text)
            title = re.sub(r"\s+\S+\s+\d\d\.\d\d\.\d\d\s+\d+\s*$", "", title).strip()
            try:
                page.goto(href, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(800)
                body = " ".join(page.inner_text("body").split())
            except Exception as e:  # noqa: BLE001
                print(f"[konect] 상세 실패 {href}: {e}")
                continue
            i = body.find(title[:15])
            body = body[i:] if i > 0 else body
            # 마감일: '마감', '~', '까지' 근처 날짜 중 가장 늦은 것
            dl = None
            near = re.findall(r"(?:마감|접수\s*기간|모집\s*기간|~|까지)[^가-힣]{0,40}?(20\d\d[.\-/년]\s*\d{1,2}[.\-/월]\s*\d{1,2})", body[:6000])
            ds = sorted(_d(DATE.search(x)) for x in near if DATE.search(x))
            if ds:
                dl = ds[-1]
            org = re.match(r"\[([^\]]+)\]", title)
            jobs.append(Job(
                source="konect", source_id=sid.group(1), title=title[:150], url=href,
                org=org.group(1) if org else "KoNECT 게시 기관", deadline=dl, start_date=posted,
                location=None, employment_type=None, raw_text=(title + " " + body)[:3000],
                extra={"site_text": body[:8000], "detail_url": href, "source_name": "KoNECT 구인게시판"},
            ))
        b.close()
    print(f"[konect] CRC·연구 관련 {len(jobs)}건")
    return jobs

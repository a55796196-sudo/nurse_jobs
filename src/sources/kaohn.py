"""직업건강협회(구 산업간호협회) 구인구직 게시판 — 보건관리자·근로자건강센터 간호사 공고.

https://www.kaohn.or.kr/board/bbs81_1 (구인). 게시판 글 본문에 지원자격·근무조건·급여가 표로 들어 있다.
GitHub Actions에서만 동작. Playwright 필요.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path

from ..models import Job

BASE = "https://www.kaohn.or.kr"
LIST = BASE + "/board/bbs81_1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
WANT = re.compile(r"간호|보건\s*관리|산업\s*보건|건강\s*관리|근로자건강센터|부속\s*의원")


def _d(y, m, d) -> str:
    return f"{int(y)}-{int(m):02d}-{int(d):02d}"


def fetch(days: int = 14, pages: int = 2) -> list[Job]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[kaohn] playwright 없음 → 건너뜀")
        return []
    try:
        seen = {k.split(":", 1)[1] for k in json.loads(Path("data/seen.json").read_text(encoding="utf-8")) if k.startswith("kaohn:")}
    except Exception:  # noqa: BLE001
        seen = set()
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    jobs: list[Job] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(user_agent=UA, locale="ko-KR").new_page()
        rows = []
        for n in range(1, pages + 1):
            try:
                page.goto(f"{LIST}?page={n}", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1500)
                rows += page.eval_on_selector_all(
                    "tr", "trs=>trs.map(t=>[t.innerText.replace(/\\s+/g,' ').trim(), (t.querySelector('a[href*=\"/board/bbs81_1/\"]')||{}).href||''])")
            except Exception as e:  # noqa: BLE001
                print(f"[kaohn] 목록 실패 p{n}: {e}")
                break
        for text, href in rows:
            sid = re.search(r"/bbs81_1/(\d+)", href or "")
            date = re.search(r"(20\d\d)\.(\d\d)\.(\d\d)", text)
            if not sid or sid.group(1) in seen or not date:
                continue
            posted = _d(*date.groups())
            if posted < since or not WANT.search(text):
                continue
            title = re.sub(r"^\d+\s+", "", text.split(date.group(0))[0]).strip()
            title = re.sub(r"\s+\S+$", "", title)           # 끝의 작성자 이름
            try:
                page.goto(href, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1200)
                body = " ".join(page.inner_text("body").split())
            except Exception as e:  # noqa: BLE001
                print(f"[kaohn] 상세 실패 {href}: {e}")
                continue
            i = body.find("모집부문")
            body = body[i:] if i >= 0 else body
            body = body.split("개인정보취급방침")[0]
            if not (re.search(r"간호|보건\s*관리|산업\s*보건", title) or "간호사" in body[:2000]):
                continue
            # 마감: '~11/30', '2026.12.05까지', '접수기간 ... ~ 2026-12-05' 등
            dl = None
            m = re.search(r"(?:마감|까지|~)\s*[:：]?\s*(20\d\d)[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", body)
            if m:
                dl = _d(*m.groups())
            org = re.match(r"\[([^\]]+)\]", title)
            loc = re.search(r"근무지\s*(?:\(센터\))?\s*([가-힣]+[시도])\s*([가-힣]+[시군구])?", body)
            jobs.append(Job(
                source="kaohn", source_id=sid.group(1), title=title[:150], url=href.split("?")[0],
                org=(org.group(1) if org else "직업건강협회 게시 기관").replace("_", " "),
                deadline=dl, start_date=posted,
                location=" ".join(x for x in loc.groups() if x) if loc else None, employment_type=None,
                raw_text=(title + " " + body)[:3000],
                extra={"site_text": body[:8000], "detail_url": href, "source_name": "직업건강협회 구인구직"},
            ))
            time.sleep(1)
        b.close()
    print(f"[kaohn] 간호·보건관리 {len(jobs)}건")
    return jobs

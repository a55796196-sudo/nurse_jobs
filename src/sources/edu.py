"""시도교육청 구인 게시판에서 보건교사(정규·기간제·대체·시간강사) 공고 수집.

- 서울: 서울교육일자리포털 (work.sen.go.kr) — 검색창에 '보건' 검색 후 목록·상세 읽기
GitHub Actions(국내 사이트 접속 가능)에서만 동작한다. Playwright 필요.
"""
from __future__ import annotations

import re

from ..models import Job

SEN_LIST = "https://work.sen.go.kr/work/search/recInfo/BD_selectSrchRecInfo.do"
# 보건교사 관련 공고만 (배움터 지킴이처럼 학교 이름에 '보건'이 들어간 경우 제외)
NURSE_SCHOOL = re.compile(r"보건\s*(교사|교원|강사|대체|시간|기간제)|과목\(담당업무\)\s*보건|보건교사|보건업무")
EXCLUDE = re.compile(r"지킴이|조리|급식|미화|배움터")


def _dt(y: str, m: str, d: str) -> str:
    return f"{y}-{int(m):02d}-{int(d):02d}"


def _text_all(page) -> str:
    out = []
    for fr in page.frames:
        try:
            out.append(" ".join(fr.inner_text("body", timeout=10000).split()))
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(out)


def fetch_seoul(page, max_items: int = 40) -> list[Job]:
    page.goto(SEN_LIST, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    box = page.query_selector("input[type='search']") or page.query_selector("input[title*='검색']")
    if not box:
        print("[edu:서울] 검색창 없음")
        return []
    box.fill("보건")
    box.press("Enter")
    page.wait_for_timeout(3000)
    links = page.eval_on_selector_all(
        "a", "els => els.map(e => [e.innerText.trim(), e.href]).filter(x => x[1].includes('BD_selectRecDetail'))")
    jobs: list[Job] = []
    for title, url in links[:max_items]:
        if EXCLUDE.search(title):
            continue
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
        except Exception as e:  # noqa: BLE001
            print(f"[edu:서울] 상세 실패 {url}: {e}")
            continue
        body = _text_all(page)
        if not NURSE_SCHOOL.search(title + " " + body[:3000]) or EXCLUDE.search(body[:600]):
            continue
        m_org = re.search(r"지원서작성\s+(\S+(?:학교|유치원))\s", body)
        m_dl = re.search(r"접수기간\s*(\d{4})\.(\d{2})\.(\d{2})\s*\S*\s*~\s*(\d{4})\.(\d{2})\.(\d{2})", body)
        m_addr = re.search(r"근무지역 주소\s+(서울특별시\s+\S+\s+[^\n]+?)\s+\S+학교\s", body)
        m_kind = re.search(r"채용직종\s+(.+?)\s+채용인원", body)
        m_cnt = re.search(r"채용인원\s+(\d+)\s*명", body)
        m_hours = re.search(r"근무시간\s+(.+?)\s+보수/임금", body)
        m_pay = re.search(r"보수/임금\s+(\S+)", body)
        gu = re.search(r"서울특별시\s+(\S+구)", body)
        sid = re.search(r"q_rcrtSn=(\d+)", url).group(1)
        job = Job(
            source="sen", source_id=sid, title=title.strip(), url=url,
            org=m_org.group(1) if m_org else "서울 학교",
            deadline=_dt(*m_dl.groups()[3:]) if m_dl else None,
            start_date=_dt(*m_dl.groups()[:3]) if m_dl else None,
            location=f"서울 {gu.group(1)}" if gu else "서울",
            employment_type=(m_kind.group(1) if m_kind else "계약제교원"),
            raw_text=body[:3000],
            extra={"site_text": body[:8000], "detail_url": url,
                   "address": m_addr.group(1) if m_addr else None,
                   "recrutNope": m_cnt.group(1) if m_cnt else None,
                   "work_hours": m_hours.group(1) if m_hours else None,
                   "pay_type": m_pay.group(1) if m_pay else None},
        )
        jobs.append(job)
    print(f"[edu:서울] 보건 관련 {len(jobs)}건")
    return jobs


def fetch() -> list[Job]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[edu] playwright 없음 → 건너뜀")
        return []
    jobs: list[Job] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        for name, fn in (("서울", fetch_seoul),):
            try:
                jobs += fn(page)
            except Exception as e:  # noqa: BLE001
                print(f"[edu:{name}] 실패: {e}")
        b.close()
    return jobs

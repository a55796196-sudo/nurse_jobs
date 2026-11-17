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


GOE_LIST = "https://www.goe.go.kr/recruit/ad/func/pb/hnfpPbancList.do?mi=10502"


def fetch_gyeonggi(page, max_items: int = 30) -> list[Job]:
    page.goto(GOE_LIST, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    box = page.query_selector("input[name*='earch']")
    if not box:
        print("[edu:경기] 검색창 없음")
        return []
    box.fill("보건")
    box.press("Enter")
    page.wait_for_timeout(3500)
    list_url = page.url
    n = len(page.query_selector_all("text=상세보기"))
    jobs: list[Job] = []
    for i in range(min(n, max_items)):
        try:
            btns = page.query_selector_all("text=상세보기")
            # 목록 카드의 글자 (제목·학교·접수기간)
            card = btns[i].evaluate("e => (e.closest('li') || e.parentElement.parentElement).innerText")
            btns[i].click()
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            body = _text_all(page)
            detail_url = page.url
        except Exception as e:  # noqa: BLE001
            print(f"[edu:경기] 상세 실패 {i}: {e}")
            body, card, detail_url = "", "", list_url
        card1 = " ".join((card or "").split())
        if not NURSE_SCHOOL.search(card1 + " " + body[:3000]) or EXCLUDE.search(card1):
            pass
        else:
            m_org = re.match(r"(\S+(?:학교|유치원))", card1)
            m_title = re.search(r"(?:마감임박|오늘마감|D-\d+)?\s*(\S.*?)\s+모집정보", card1)
            m_dl = re.search(r"접수기간\s*(\d{4})/(\d{2})/(\d{2})\s*~\s*(\d{4})/(\d{2})/(\d{2})", card1)
            m_pay = re.search(r"모집정보\s+(\S+)", card1)
            m_cnt = re.search(r"채용인원\s+(\d+)", card1)
            m_kind = re.search(r"직무분야\s+(\S+)", card1)
            m_addr = re.search(r"(경기도\s+\S+[시군]\s+[^\n]{3,40}?)(?:\s{2}|\s+\S+학교|$)", body)
            sid = re.findall(r"\d+", detail_url)[-1] if re.findall(r"\d+", detail_url) else f"{i}"
            title = re.sub(r"^\S+\s+\d{2,3}-\d{3,4}-\d{4}\s+등록일\s*:\s*\S+\s+조회수\s*:\s*\d+\s*", "", m_title.group(1)) if m_title else "보건교사 채용"
            city = re.search(r"경기도\s+(\S+[시군])", body)
            jobs.append(Job(
                source="goe", source_id=sid, title=title, url=detail_url if detail_url != list_url else GOE_LIST,
                org=m_org.group(1) if m_org else "경기 학교",
                deadline="-".join(m_dl.groups()[3:]) if m_dl else None,
                start_date="-".join(m_dl.groups()[:3]) if m_dl else None,
                location=f"경기 {city.group(1)}" if city else "경기",
                employment_type=m_kind.group(1) if m_kind else "계약제교원",
                raw_text=(card1 + " " + body)[:3000],
                extra={"site_text": body[:8000], "list_card": card1, "detail_url": detail_url,
                       "address": m_addr.group(1).strip() if m_addr else None,
                       "recrutNope": m_cnt.group(1) if m_cnt else None,
                       "pay_type": m_pay.group(1) if m_pay else None},
            ))
        try:
            page.goto(list_url, wait_until="networkidle", timeout=60000)
            box = page.query_selector("input[name*='earch']")
            if box:
                box.fill("보건"); box.press("Enter"); page.wait_for_timeout(3000)
        except Exception:  # noqa: BLE001
            break
    print(f"[edu:경기] 보건 관련 {len(jobs)}건")
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
        for name, fn in (("서울", fetch_seoul), ("경기", fetch_gyeonggi)):
            try:
                jobs += fn(page)
            except Exception as e:  # noqa: BLE001
                print(f"[edu:{name}] 실패: {e}")
        b.close()
    return jobs

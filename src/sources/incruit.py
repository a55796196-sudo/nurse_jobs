"""인크루트 채용검색에서 CRC·CRA·연구간호사·보건관리자·보험심사 등 민간 공고 수집.

잡코리아·사람인·원티드는 GitHub Actions 서버 접속을 막아서 못 읽는다 (2026-11 확인).
인크루트는 목록·상세(jobpostcont iframe) 모두 열린다. Playwright 필요.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

from ..models import Job

LIST = "https://search.incruit.com/list/search.asp?col=job&kw={q}&sortfield=reg"
VIEW = "https://job.incruit.com/jobdb_info/jobpost.asp?job={no}"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
# 검색어 → 제목에 꼭 들어가야 하는 말, 연구직 여부
KEYWORDS = {
    "CRC": (r"CRC|코디네이터|연구\s*간호", True),
    "CRA": (r"CRA|Clinical\s*Research|모니터링|임상\s*운영", True),
    "연구간호사": (r"연구\s*간호|임상\s*(시험|연구)", True),
    "임상연구": (r"CRA|CRC|연구\s*간호|임상\s*연구\s*(원|팀|간호|코디|관리)|임상\s*(시험|연구)\s*(지원|센터|간호|코디|운영)|임상\s*수행", True),
    "임상시험": (r"CRA|CRC|연구\s*간호|임상\s*시험\s*(지원|센터|간호|코디|담당|운영)|임상\s*운영|임상\s*수행", True),
    "SMO": (r"CRC|CRA|SMO|에스엠오|코디네이터", True),
    "보건관리자": (r"보건\s*관리", False),
    "산업간호사": (r"산업\s*간호|보건\s*관리", False),
    "보험심사": (r"보험\s*심사|심사\s*간호|청구", False),
}
EXCLUDE = re.compile(r"병리|방사선|심리|화장품|피부\s*임상|통계|Writer|BD|영업|Data|데이터|동물|실험\s*보조|약물전달|생산|Biostat|과학자|"
                     r"병동|외래|수술실|응급실|중환자|요양병원|3교대|2교대|야간|D/E|간호조무|Ambassador|Retail|Advisor", re.I)
RESEARCH_DAYS, OTHER_DAYS = 10, 3


def _clean(s: str) -> str:
    import html as H
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def _rows(html: str) -> list[dict]:
    out = []
    for chunk in re.split(r'<ul class="c_row" jobno="', html)[1:]:
        no = chunk.split('"', 1)[0]
        org = re.search(r'class="cpname"[^>]*>(.*?)</a>', chunk, re.S)
        title = re.search(r'<div class="cl_top"><a href="https://job\.incruit\.com/jobdb_info/jobpost\.asp\?job=' + no + r'[^"]*"[^>]*>(.*?)</a>', chunk, re.S)
        md = re.search(r'<div class="cl_md">(.*?)</div>', chunk, re.S)
        last = re.search(r'<div class="cell_last"><div class="cl_btm">(.*?)</div>', chunk, re.S)
        ago = re.search(r"\((\d+)일전 등록\)", chunk)
        out.append({
            "no": no, "org": _clean(org.group(1)) if org else "", "title": _clean(title.group(1)) if title else "",
            "meta": [_clean(x) for x in re.findall(r"<span>(.*?)</span>", md.group(1))] if md else [],
            "last": _clean(last.group(1)) if last else "",
            "ago": int(ago.group(1)) if ago else (0 if re.search(r"(시간|분)전 등록|오늘", chunk) else None),
        })
    return out


def _deadline(main: str) -> str | None:
    m = re.search(r"마감\s*(20\d\d)\.(\d{1,2})\.(\d{1,2})", main)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


def fetch() -> list[Job]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[incruit] playwright 없음 → 건너뜀")
        return []
    try:
        seen = {k.split(":", 1)[1] for k in json.loads(Path("data/seen.json").read_text(encoding="utf-8")) if k.startswith("incruit:")}
    except Exception:  # noqa: BLE001
        seen = set()
    found: dict[str, dict] = {}
    jobs: list[Job] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(user_agent=UA, locale="ko-KR")
        page = ctx.new_page()
        for kw, (need, research) in KEYWORDS.items():
            limit = RESEARCH_DAYS if research else OTHER_DAYS
            try:
                page.goto(LIST.format(q=quote(kw)), wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                rows = _rows(page.content())
            except Exception as e:  # noqa: BLE001
                print(f"[incruit] 검색 실패 {kw}: {e}")
                page.close()
                page = ctx.new_page()
                continue
            hit = 0
            for r in rows:
                if r["ago"] is not None and r["ago"] > limit:
                    continue
                if not re.search(need, r["title"], re.I) or EXCLUDE.search(r["title"]):
                    continue
                if r["no"] in found or r["no"] in seen:
                    continue
                r["kw"] = kw
                found[r["no"]] = r
                hit += 1
            print(f"[incruit] {kw}: 목록 {len(rows)}건 중 {hit}건")
            time.sleep(2)
        for no, r in list(found.items())[:40]:
            url = VIEW.format(no=no)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3500)
                main = " ".join(page.inner_text("body").split())
                cont = ""
                for fr in page.frames:
                    if "jobpostcont" in fr.url:
                        cont = " ".join(fr.inner_text("body").split())
            except Exception as e:  # noqa: BLE001
                print(f"[incruit] 상세 실패 {no}: {e}")
                page.close()
                page = ctx.new_page()
                continue
            i = main.find(r["title"][:12])
            head = main[i:] if i > 0 else main
            head = head.split("게시중단 요청")[0]
            meta = r["meta"]
            emp = next((m for m in meta if re.search(r"정규직|계약직|인턴|파견|위촉|프리랜서", m)), None)
            m_emp = re.search(r"고용형태\s*(.+?)\s*(?:경력|근무지역)", head)
            jobs.append(Job(
                source="incruit", source_id=no, title=r["title"][:150], url=url,
                org=r["org"] or "인크루트 게시 기관", deadline=_deadline(head),
                start_date=(dt.date.today() - dt.timedelta(days=r["ago"] or 0)).isoformat(),
                location=meta[0] if meta else None,
                employment_type=(m_emp.group(1) if m_emp else emp),
                raw_text=(r["title"] + " " + cont + " " + head)[:3000],
                extra={"site_text": head[:4000], "origin_text": cont[:8000], "list_text": " / ".join(meta + [r["last"]]),
                       "source_name": "인크루트",
                       # 일부 공고는 본문 자리에 인크루트 AI가 쓴 요약 기사만 있음 → 원문 아님 (기관 홈페이지 확인 필요)
                       "ai_article": "AI가 작성한 기사" in main},
            ))
            time.sleep(1.5)
        b.close()
    print(f"[incruit] 관련 {len(jobs)}건")
    return jobs

"""고용24(구 워크넷) 채용정보 검색 화면에서 보건관리자·산업간호사·연구간호사·CRC 등 민간 공고 수집.

공개 검색 결과(로그인 불필요)를 읽는다. GitHub Actions(국내 사이트 접속 가능)에서만 동작. Playwright 필요.
"""
from __future__ import annotations

import datetime as dt
import html as H
import re
import time
from urllib.parse import quote

from ..models import Job

BASE = "https://www.work24.go.kr"
LIST = BASE + "/wk/a/b/1200/retriveDtlEmpSrchList.do"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
# 검색어 → 제목에 꼭 들어가야 하는 말 (검색이 직무내용까지 넓게 잡아서 제목으로 한 번 더 거름)
KEYWORDS = {
    "보건관리자": r"보건관리자|보건\s*관리",
    "산업간호사": r"산업\s*간호|보건관리자",
    "산업보건": r"산업\s*보건|보건관리|산업\s*간호",
    "연구간호사": r"연구\s*간호|CRC|임상연구|임상시험",
    "CRC": r"CRC|코디네이터|임상연구|연구\s*간호",
    "임상연구코디네이터": r"CRC|코디네이터|임상연구",
    "임상시험 간호사": r"임상시험|임상연구|연구\s*간호|CRC",
    "임상시험센터": r"임상시험|임상연구|연구\s*간호|CRC",
    "보험심사 간호사": r"보험\s*심사|심사\s*간호|청구",
    "심사간호사": r"심사|청구|적정성",
    "간호사 사무": r"간호사",
}
NOT_CLINICAL_HINT = re.compile(r"병동|외래|수술실|응급실|중환자|요양병원|3교대|2교대|야간전담|간호조무")


def _clean(s: str) -> str:
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S)
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", s)).split()).lstrip("> ").strip()


def _rows(html: str) -> list[dict]:
    out = []
    for chunk in re.split(r'<tr id="list\d+"', html)[1:]:
        chunk = chunk.split("</tr>")[0]
        auth = re.search(r"wantedAuthNo=([A-Za-z0-9]+)", chunk)
        if not auth:
            continue
        # 공고마다 정보제공처 코드가 다름 (고용24 자체 VALIDATION, 잡코리아 CJK, 사람인 CSI 등) → 목록의 링크를 그대로 씀
        href = re.search(r'href="(/wk/a/b/1500/empDetailAuthView\.do\?[^"]*wantedAuthNo=' + auth.group(1) + r'[^"]*)"', chunk)
        links = re.findall(r"<a[^>]*wantedAuthNo=[^>]*>(.*?)</a>", chunk, re.S)
        title = _clean(links[0]) if links else ""
        text = _clean(chunk)
        dl = re.search(r"마감일\s*:\s*(20\d\d-\d\d-\d\d)", text)
        reg = re.search(r"등록일\s*:\s*(20\d\d-\d\d-\d\d)", text)
        out.append({"auth": auth.group(1), "title": title, "text": text,
                    "href": BASE + H.unescape(href.group(1)) if href else None,
                    "deadline": dl.group(1) if dl else None, "posted": reg.group(1) if reg else None})
    return out


def fetch(days: int = 3, pages: int = 3, max_detail: int = 40) -> list[Job]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[work24] playwright 없음 → 건너뜀")
        return []
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    found: dict[str, dict] = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(user_agent=UA, locale="ko-KR").new_page()
        for kw, need in KEYWORDS.items():
            hit, total = 0, 0
            for pg_no in range(1, pages + 1):
                # keywordWantedTitle=Y: 제목에서만 검색 (안 먹히면 전체 검색 결과를 제목으로 거름)
                url = (f"{LIST}?srcKeyword={quote(kw)}&keywordWantedTitle=Y&keywordFlag=&pageIndex={pg_no}"
                       f"&sortField=DATE&sortOrderBy=DESC")
                try:
                    page.goto(url, wait_until="networkidle", timeout=90000)
                    page.wait_for_timeout(1500)
                    rows = _rows(page.content())
                except Exception as e:  # noqa: BLE001
                    print(f"[work24] 검색 실패 {kw} p{pg_no}: {e}")
                    break
                total += len(rows)
                old_seen = False
                for r in rows:
                    if r["posted"] and r["posted"] < since:
                        old_seen = True
                        continue
                    if not re.search(need, r["title"], re.I) or r["auth"] in found:
                        continue
                    if kw == "간호사 사무" and NOT_CLINICAL_HINT.search(r["title"]):
                        continue
                    r["kw"] = kw
                    found[r["auth"]] = r
                    hit += 1
                time.sleep(2)
                if len(rows) < 10 or old_seen:
                    break
            print(f"[work24] {kw}: 목록 {total}건 중 {hit}건")
        jobs: list[Job] = []
        for n, (auth, r) in enumerate(found.items()):
            url = r.get("href") or f"{BASE}/wk/a/b/1500/empDetailAuthView.do?wantedAuthNo={auth}&infoTypeCd=VALIDATION&infoTypeGroup=tb_workinfoworknet"
            body = ""
            if n < max_detail:
                try:
                    page.goto(url, wait_until="networkidle", timeout=90000)
                    page.wait_for_timeout(1200)
                    body = " ".join(page.inner_text("body").split())
                    i = body.find(r["title"][:15])
                    body = body[i:] if i > 0 else ""   # 외부 제공 공고는 본문이 없음
                    time.sleep(1.5)
                except Exception as e:  # noqa: BLE001
                    print(f"[work24] 상세 실패 {auth}: {e}")
            text = r["text"]
            company = text.split(r["title"][:10])[0].strip() if r["title"] else ""
            company = re.sub(r"\s+\S*\(주\)\S*$|\s+$", "", company)[:40] or "기업"
            after = text.split(r["title"][:15], 1)[-1]
            after = re.sub(r"채용시까지|채용시", " ", after)
            loc = re.search(r"(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|충청|전북|전남|전라|경북|경남|경상|제주)\S*\s+(\S+[시군구])", after)
            jobs.append(Job(
                source="work24", source_id=auth, title=r["title"][:150], url=url,
                org=company, deadline=r["deadline"], start_date=r["posted"],
                location=" ".join(loc.groups()) if loc else None, employment_type=None,
                raw_text=(r["title"] + " " + text + " " + body)[:3000],
                extra={"list_text": text[:1500], "site_text": body[:8000], "detail_url": url,
                       "search_kw": r["kw"], "source_name": "고용24"},
            ))
        b.close()
    print(f"[work24] 관련 {len(jobs)}건")
    return jobs

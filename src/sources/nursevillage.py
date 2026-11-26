"""널스빌리지 채용공고 (간호사 전용 채용 모음) — 병원 안 비임상(보험심사·연구간호사·감염관리·QI 등) 공고를 고른다.

목록은 스크롤할 때마다 더 불러오는 화면이라 Playwright로 열어 내린다. 상세 화면에는 정리된 본문(주요 업무·지원 자격·
근무 조건·전형)과 원문 '공고 보러가기' 링크가 있다. GitHub Actions에서만 동작.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path

from ..models import Job

BASE = "https://www.nursevillage.com"
LIST = BASE + "/job/job-posting"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
# 제목에 이 말이 있어야 후보 (병동·외래 등 임상 공고가 대부분이라 비임상 직무만)
WANT = re.compile(r"보험\s*심사|심사\s*(팀|실|과|간호)|청구|연구\s*간호|연구원|CRC|CRA|임상\s*(시험|연구)|코디네이터|보건\s*관리|산업\s*간호|"
                  r"QI|적정성|질\s*향상|감염\s*관리|환자\s*안전|보건\s*교사|보건실|건강\s*(관리실|센터|증진)|검진\s*센터\s*상담|간호\s*행정|"
                  r"교육\s*전담|PA\b|의료\s*질|건강\s*상담|보건소", re.I)
SKIP = re.compile(r"성형|피부과|상담\s*실장|실장|코디네이터/상담|간호조무|조무사|아르바이트|요양원\s*시설장", re.I)


def _seen() -> set[str]:
    try:
        return {k.split(":", 1)[1] for k in json.loads(Path("data/seen.json").read_text(encoding="utf-8")) if k.startswith("nursevillage:")}
    except Exception:  # noqa: BLE001
        return set()


def _deadline(text: str, today: dt.date) -> tuple[str | None, str | None]:
    """'12/01(화) 23:59 ... 마감' 같은 표기에서 마감일·시각."""
    m = re.search(r"(\d{1,2})/(\d{1,2})\s*\([월화수목금토일]\)\s*(\d{1,2}:\d{2})?[^가-힣]{0,20}[가-힣\s]{0,12}마감", text)
    if not m:
        return None, None
    mo, d = int(m.group(1)), int(m.group(2))
    year = today.year + (1 if mo < today.month - 1 else 0)
    try:
        return dt.date(year, mo, d).isoformat(), m.group(3)
    except ValueError:
        return None, None


def fetch(scrolls: int = 12, max_detail: int = 30) -> list[Job]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[nursevillage] playwright 없음 → 건너뜀")
        return []
    seen, today, jobs = _seen(), dt.date.today(), []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(user_agent=UA, locale="ko-KR")
        page = ctx.new_page()
        try:
            page.goto(LIST, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(2000)
            for _ in range(scrolls):          # 아래로 내릴 때마다 최신순으로 더 불러옴
                page.mouse.wheel(0, 20000)
                page.wait_for_timeout(1500)
            links = page.eval_on_selector_all(
                "a", "as=>as.map(a=>[a.innerText.trim().replace(/\\s+/g,' '), a.href])")
        except Exception as e:  # noqa: BLE001
            print(f"[nursevillage] 목록 실패: {e}")
            b.close()
            return []
        cands: dict[str, list[str]] = {}
        for text, href in links:
            m = re.search(r"/job-posting/(\d+)", href or "")
            if not m or m.group(1) in cands or m.group(1) in seen:
                continue
            parts = [x.strip() for x in text.split(" · ")]
            title = parts[1] if len(parts) > 1 else text
            if WANT.search(title) and not SKIP.search(title):
                cands[m.group(1)] = parts
        print(f"[nursevillage] 목록 {len(links)}개 링크 중 후보 {len(cands)}건")
        for sid, parts in list(cands.items())[:max_detail]:
            url = f"{LIST}/{sid}"
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(1500)
                body = " ".join(page.inner_text("body").split())
                orig = page.eval_on_selector_all(
                    "a", "as=>as.filter(a=>/공고 보러가기|원문|지원하기/.test(a.innerText)).map(a=>a.href)")
            except Exception as e:  # noqa: BLE001
                print(f"[nursevillage] 상세 실패 {sid}: {e}")
                page.close()
                page = ctx.new_page()
                continue
            org, title = parts[0], parts[1] if len(parts) > 1 else parts[0]
            i = body.find(title[:15])
            body = body[i:] if i >= 0 else body
            body = body.split("병원 후기 정보")[0]
            dl, dl_time = _deadline(body, today)
            if dl and dl < today.isoformat():
                continue
            origin = next((u for u in orig if u and "nursevillage.com" not in u), None)
            jobs.append(Job(
                source="nursevillage", source_id=sid, title=title[:150], url=origin or url, org=org,
                deadline=dl, start_date=today.isoformat(),
                location=parts[2] if len(parts) > 2 else None,
                employment_type=parts[3] if len(parts) > 3 and parts[3] != "기타" else None,
                raw_text=(title + " " + body)[:3000],
                extra={"site_text": body[:8000], "detail_url": url, "origin_url": origin, "deadline_time": dl_time,
                       "list_text": " · ".join(parts), "source_name": "널스빌리지",
                       # 널스빌리지 상세는 원문을 정리한 요약(AI 요약 표기)이므로 원문 링크로 대조
                       "summary_page": "AI 요약" in body},
            ))
            time.sleep(1)
        b.close()
    print(f"[nursevillage] 비임상 후보 {len(jobs)}건")
    return jobs

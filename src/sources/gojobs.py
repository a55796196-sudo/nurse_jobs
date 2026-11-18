"""나라일터 공고(보건소·치매안심센터 등 지자체 간호 공고) 수집.

나라일터(gojobs.go.kr) 목록은 자동 브라우저에서 비어 나오므로, 같은 공고를 그대로 싣는
정책브리핑 채용정보(korea.kr/archive/recruitInfoList.do)에서 최근 공고를 넘겨보며 고른다.
GitHub Actions(국내 사이트 접속 가능)에서만 동작한다. Playwright 필요.
"""
from __future__ import annotations

import datetime as dt
import re

from ..models import Job

BASE = "https://www.korea.kr"
LIST = BASE + "/archive/recruitInfoList.do"
# 목록(제목+기관)에서 먼저 거르는 단어 → 상세 본문에 '간호'가 있어야 최종 채택
HINT = re.compile(r"간호|보건소|보건지소|보건진료|치매안심|방문건강|정신건강|건강증진|감염병|예방접종|모자보건")
EXCLUDE = re.compile(r"합격자|결과\s*공고|면접시험|서류전형|시험\s*일정|청소|조리|미화|운전")
AREAS = ("서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남",
         "전북", "전남", "경북", "경남", "제주", "충청북도", "충청남도", "전라북도", "전북특별자치도",
         "전라남도", "경상북도", "경상남도", "강원특별자치도", "제주특별자치도")


def _d(s: str) -> str | None:
    m = re.search(r"(20\d\d)\.(\d{1,2})\.(\d{1,2})", s or "")
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


def _rows(page) -> list[dict]:
    return page.eval_on_selector_all(
        "a[href*='recruitInfoView']",
        """els => els.map(e => {
            const row = e.closest('tr') || e.closest('li') || e.parentElement.parentElement;
            return {title: e.innerText.trim(), href: e.getAttribute('href'), row: row ? row.innerText : ''};
        })""")


def fetch(days: int = 2, max_pages: int = 40) -> list[Job]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[gojobs] playwright 없음 → 건너뜀")
        return []
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    cands: dict[str, dict] = {}
    jobs: list[Job] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        prev_first = None
        n = 0
        for n in range(1, max_pages + 1):
            try:
                page.goto(f"{LIST}?pageIndex={n}", wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(800)
                rows = _rows(page)
            except Exception as e:  # noqa: BLE001
                print(f"[gojobs] 목록 실패 p{n}: {e}")
                break
            if not rows or rows[0]["href"] == prev_first:
                break  # 쪽 넘김이 안 되거나 끝
            prev_first = rows[0]["href"]
            oldest = None
            for r in rows:
                row = " ".join(r["row"].split())
                dates = re.findall(r"20\d\d\.\d{1,2}\.\d{1,2}", row)
                posted = _d(dates[0]) if dates else None
                oldest = posted or oldest
                if HINT.search(row) and not EXCLUDE.search(r["title"]):
                    sid = re.search(r"dataId=(\d+)", r["href"]).group(1)
                    org = row.replace(r["title"], "").strip()
                    org = re.split(r"\s20\d\d\.", org)[0].strip()
                    cands[sid] = {"title": r["title"], "org": org, "posted": posted,
                                  "deadline": _d(dates[1]) if len(dates) > 1 else None}
            if oldest and oldest < since:
                break
        print(f"[gojobs] 목록 {n}쪽까지, 후보 {len(cands)}건")
        for sid, c in cands.items():
            url = f"{BASE}/archive/recruitInfoView.do?dataId={sid}"
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(800)
                body = " ".join(page.inner_text("body").split())
            except Exception as e:  # noqa: BLE001
                print(f"[gojobs] 상세 실패 {url}: {e}")
                continue
            i = body.find(c["title"][:20])
            body = body[i:] if i > 0 else body
            if "간호" not in c["title"] + body[:6000]:
                continue
            orgs = c["org"] or ""
            loc = next((a for a in AREAS if a in orgs + " " + c["title"]), None)
            city = re.search(r"(\S+[시군구])(?:\s|보건|$)", orgs)
            last = orgs.split()[-1] if orgs else "지자체"
            jobs.append(Job(
                source="gojobs", source_id=sid, title=c["title"], url=url,
                org=last, deadline=c["deadline"], start_date=c["posted"],
                location=" ".join(x for x in (loc, city.group(1) if city else None) if x) or None,
                employment_type="기간제" if "기간제" in c["title"] + body[:3000] else None,
                raw_text=(c["title"] + " " + body)[:3000],
                extra={"site_text": body[:8000], "detail_url": url, "org_path": orgs},
            ))
        b.close()
    print(f"[gojobs] 간호 관련 {len(jobs)}건")
    return jobs

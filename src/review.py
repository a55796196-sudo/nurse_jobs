"""블로그 임시저장 전 검토.

python -m src.main review YYYY-MM-DD   자동 점검 + 눈으로 볼 한 장짜리 시트(docs/DAY/review-sheet.jpg)
python -m src.main linkcheck YYYY-MM-DD (GitHub Actions 전용) 고른 공고 링크가 실제 공고로 열리는지
python -m src.main ready YYYY-MM-DD    검토 완료 표시(docs/DAY/ready.json) → 노트북 임시저장이 이걸 보고 시작
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .models import Job

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA = ROOT / "data"
KST = timezone(timedelta(hours=9))
BADGE = re.compile(r"(대기업|중견|중소|강소|코스피|코스닥|가족|외국계|벤처)\s*$")


def _jobs(day: str) -> list[Job]:
    for p in (DATA / "inbox" / f"{day}.json", DATA / "jobs" / f"{day}.json"):
        if p.exists():
            return [Job.from_dict(x) for x in json.loads(p.read_text(encoding="utf-8"))]
    raise SystemExit(f"{day} 데이터가 없습니다")


def _picks(day: str) -> list[Job]:
    from .blog import picks
    return picks([j for j in _jobs(day) if j.is_target])


def issues(day: str) -> list[str]:
    from .main import _missing
    out = []
    today = date.fromisoformat(day)
    seen = set()
    for n, j in enumerate(_picks(day), start=1):
        tag = f"글{n} {j.org}"
        miss = _missing(j)
        if miss:
            out.append(f"{tag}: 원문에 있는데 비어 있음 → {', '.join(miss)}")
        if not j.deadline:
            out.append(f"{tag}: 마감일 없음")
        elif j.deadline < today.isoformat():
            out.append(f"{tag}: 이미 마감 ({j.deadline})")
        if not j.url:
            out.append(f"{tag}: 지원 링크 없음")
        if j.source == "work24" and re.search(r"wantedAuthNo=\d+&infoTypeCd=VALIDATION", j.url or ""):
            out.append(f"{tag}: 고용24 외부 공고인데 VALIDATION 링크 (열리지 않음)")
        if BADGE.search(j.org or ""):
            out.append(f"{tag}: 기관명에 기업 구분 표시가 붙음 ({j.org})")
        if re.fullmatch(r"\S{1,3}구", (j.org or "").strip()):
            out.append(f"{tag}: 기관명이 '{j.org}'뿐 — 도시 이름 붙이기")
        if len(j.qualifications or []) <= 1:
            out.append(f"{tag}: 지원자격이 {len(j.qualifications or [])}개뿐 — 원문 전체 확인")
        if j.deadline_time and j.deadline_time not in " ".join(str(v) for v in (j.raw_text, *(j.extra or {}).values())):
            out.append(f"{tag}: 마감 시각 {j.deadline_time}이 원문에서 안 보임 — 확인")
        key = (j.org, j.job_role)
        if key in seen:
            out.append(f"{tag}: 같은 기관·직무 글이 두 개")
        seen.add(key)
    lc = DATA / "linkcheck" / f"{day}.json"
    if lc.exists():
        for k, v in json.loads(lc.read_text(encoding="utf-8")).items():
            if not v.get("ok"):
                out.append(f"링크 확인 실패 {k}: {v.get('why')}")
    else:
        out.append("링크 확인 결과 없음 (review.yml 실행 필요)")
    return out


def sheet(day: str) -> Path:
    """썸네일 + 인스타 표지를 한 장에 모아 눈으로 검토."""
    from PIL import Image
    d = DOCS / day
    thumbs = sorted(d.glob("thumb-[0-9][0-9].png"))
    covers = sorted(d.glob("ig-[0-9][0-9]-1.jpg"))
    ims = [Image.open(p).convert("RGB").resize((360, 360)) for p in thumbs] + \
          [Image.open(p).convert("RGB").resize((288, 360)) for p in covers]
    if not ims:
        raise SystemExit("이미지가 없습니다 (build 먼저)")
    w = sum(i.width + 12 for i in ims)
    out = Image.new("RGB", (w, 360), "white")
    x = 0
    for i in ims:
        out.paste(i, (x, 0)); x += i.width + 12
    p = d / "review-sheet.jpg"
    out.save(p, quality=85)
    return p


def linkcheck(day: str) -> None:
    """(Actions) 고른 공고 링크를 열어 실제 공고(기관명·제목 일부)가 보이는지 확인."""
    from playwright.sync_api import sync_playwright
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context(user_agent=ua, locale="ko-KR").new_page()
        for n, j in enumerate(_picks(day), start=1):
            url = j.extra.get("alio_url") or j.url
            key = f"글{n} {j.org}"
            try:
                r = pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(3000)
                text = " ".join(" ".join(fr.inner_text("body").split()) for fr in pg.frames if fr.url.startswith("http"))[:200000]
                words = [w for w in re.split(r"[\s\[\]()·,/]+", f"{j.org} {j.title}") if len(w) >= 2][:12]
                hit = sum(1 for w in words if w in text)
                ok = (r is None or r.status < 400) and hit >= max(2, len(words) // 3)
                res[key] = {"url": url, "ok": ok, "status": r.status if r else None, "hit": f"{hit}/{len(words)}",
                            "why": "" if ok else "페이지에 공고 내용이 안 보임 (링크 확인)"}
            except Exception as e:  # noqa: BLE001
                res[key] = {"url": url, "ok": False, "why": f"열기 실패: {str(e)[:120]}"}
            print(key, res[key])
        b.close()
    out = DATA / "linkcheck" / f"{day}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def ready(day: str) -> None:
    left = issues(day)
    p = DOCS / day / "ready.json"
    p.write_text(json.dumps({"reviewed_at": datetime.now(KST).isoformat(timespec="minutes"),
                             "remaining_issues": left}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"검토 완료 표시: {p}" + (f" (남은 메모 {len(left)}건)" if left else ""))

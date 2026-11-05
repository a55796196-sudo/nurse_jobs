"""매일 실행: 수집 → 중복 제거 → AI 분류 → 카드뉴스·블로그 초안 생성.

사용법:
  python -m src.main            # 실제 수집
  python -m src.main --sample   # 샘플 데이터로 동작 확인 (API 키 불필요)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .classify import classify
from .models import CATEGORIES, Job
from .render import render_all
from .site import build_day, build_index
from .sources import alio, saramin

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
SEEN_FILE = DATA / "seen.json"
KST = timezone(timedelta(hours=9))


def load_seen() -> dict[str, str]:
    try:
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_seen(seen: dict[str, str], today: str) -> None:
    # 90일 지난 기록은 정리
    cutoff = (datetime.fromisoformat(today) - timedelta(days=90)).date().isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    DATA.mkdir(exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def collect(sample: bool) -> list[Job]:
    if sample:
        raw = json.loads((ROOT / "tests" / "sample_jobs.json").read_text(encoding="utf-8"))
        return [Job.from_dict(d) for d in raw]
    jobs: list[Job] = []
    for name, fn in (("alio", alio.fetch), ("saramin", saramin.fetch)):
        try:
            jobs += fn()
        except Exception as e:  # 한 출처가 실패해도 나머지는 계속
            print(f"[{name}] 수집 실패: {e}")
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="샘플 데이터로 실행")
    args = ap.parse_args()

    today = datetime.now(KST).date()
    seen = {} if args.sample else load_seen()

    jobs = collect(args.sample)
    # 같은 공고 중복 제거 (출처 ID + 기관·제목 기준)
    uniq: dict[str, Job] = {}
    titles = set()
    for j in jobs:
        sig = (j.org.strip(), j.title.strip())
        if j.key in seen or j.key in uniq or sig in titles:
            continue
        if j.deadline and j.deadline < today.isoformat():
            continue
        uniq[j.key] = j
        titles.add(sig)
    new_jobs = list(uniq.values())
    print(f"새 공고 {len(new_jobs)}건 (전체 수집 {len(jobs)}건)")

    classify(new_jobs)
    # 분류에 실패한(is_target=None) 공고는 seen에 넣지 않아 다음 실행 때 다시 시도
    for j in new_jobs:
        if j.is_target is not None:
            seen[j.key] = today.isoformat()

    targets = [j for j in new_jobs if j.is_target]
    order = list(CATEGORIES)
    targets.sort(key=lambda j: (order.index(j.category), j.deadline or "9999"))
    print(f"탈임상 공고 {len(targets)}건: " + ", ".join(f"{c} {sum(j.category == c for j in targets)}" for c in order))

    if not args.sample:
        save_seen(seen, today.isoformat())

    if not targets:
        print("오늘은 새 탈임상 공고가 없어 페이지를 만들지 않습니다.")
        build_index(DOCS)
        return

    out = DOCS / today.isoformat()
    cards = render_all(targets, today, out)
    build_day(targets, today, DOCS, cards)
    build_index(DOCS)
    print(f"완료: {out}/index.html (카드 {len(cards)}장)")


if __name__ == "__main__":
    main()

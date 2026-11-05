"""탈임상 공고 파이프라인.

  python -m src.main collect          # 수집 + 중복 제거 → data/inbox/날짜.json (GitHub Actions, 무료)
  python -m src.main check [날짜]      # inbox 파일 분류가 다 채워졌는지 검사
  python -m src.main build [날짜]      # 분류된 inbox → 카드뉴스·블로그·작업실 페이지 생성
  python -m src.main run              # collect + Claude API 분류 + build 한 번에 (API 키 있을 때만)
  python -m src.main sample           # 샘플 데이터로 동작 확인

분류는 두 가지 방법 중 하나로 합니다.
  A) 예약된 Claude Code 세션이 inbox 파일을 직접 읽고 분류 필드를 채움 (구독 사용, 추가 비용 없음)
  B) ANTHROPIC_API_KEY 가 있으면 run 명령이 Claude API로 분류 (API 요금 발생)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import CATEGORIES, Job
from .render import render_all
from .site import build_day, build_index
from .sources import alio, saramin

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INBOX = DATA / "inbox"
DOCS = ROOT / "docs"
SEEN_FILE = DATA / "seen.json"
KST = timezone(timedelta(hours=9))


def today_kst() -> str:
    return datetime.now(KST).date().isoformat()


def load_seen() -> dict[str, str]:
    try:
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_seen(seen: dict[str, str], today: str) -> None:
    cutoff = (datetime.fromisoformat(today) - timedelta(days=90)).date().isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    DATA.mkdir(exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def read_jobs(path: Path) -> list[Job]:
    return [Job.from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))]


def write_jobs(path: Path, jobs: list[Job]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([j.to_dict() for j in jobs], ensure_ascii=False, indent=1), encoding="utf-8")


def collect() -> Path | None:
    today = today_kst()
    seen = load_seen()
    jobs: list[Job] = []
    for name, fn in (("alio", alio.fetch), ("saramin", saramin.fetch)):
        try:
            jobs += fn()
        except Exception as e:  # 한 출처가 실패해도 나머지는 계속
            print(f"[{name}] 수집 실패: {e}")

    uniq: dict[str, Job] = {}
    titles = set()
    for j in jobs:
        sig = (j.org.strip(), j.title.strip())
        if j.key in seen or j.key in uniq or sig in titles:
            continue
        if j.deadline and j.deadline < today:
            continue
        uniq[j.key] = j
        titles.add(sig)
    new_jobs = list(uniq.values())
    print(f"새 공고 {len(new_jobs)}건 (전체 수집 {len(jobs)}건)")

    for j in new_jobs:
        seen[j.key] = today
    save_seen(seen, today)
    if not new_jobs:
        return None
    path = INBOX / f"{today}.json"
    if path.exists():  # 같은 날 두 번 실행되면 합치기
        new_jobs = read_jobs(path) + new_jobs
    write_jobs(path, new_jobs)
    print(f"저장: {path}")
    return path


def check(path: Path) -> list[str]:
    errors = []
    for i, j in enumerate(read_jobs(path)):
        if j.is_target is None:
            errors.append(f"#{i} 미분류: {j.title}")
        elif j.is_target and j.category not in CATEGORIES:
            errors.append(f"#{i} 잘못된 category '{j.category}': {j.title}")
        elif j.is_target and not (j.summary and j.job_role):
            errors.append(f"#{i} summary/job_role 비어있음: {j.title}")
    return errors


def build(path: Path, day: str, archive: bool = True) -> None:
    errors = check(path)
    if errors:
        sys.exit("분류가 덜 끝났습니다:\n" + "\n".join(errors[:20]))
    jobs = read_jobs(path)
    targets = [j for j in jobs if j.is_target]
    order = list(CATEGORIES)
    targets.sort(key=lambda j: (order.index(j.category), j.deadline or "9999"))
    print(f"탈임상 {len(targets)}건 / 전체 {len(jobs)}건: "
          + ", ".join(f"{c} {sum(j.category == c for j in targets)}" for c in order))

    from datetime import date
    d = date.fromisoformat(day)
    if targets:
        out = DOCS / day
        cards = render_all(targets, d, out)
        build_day(targets, d, DOCS, cards)
        print(f"완료: docs/{day}/index.html (카드 {len(cards)}장)")
    else:
        print("오늘은 탈임상 공고가 없어 페이지를 만들지 않습니다.")
    build_index(DOCS)
    if archive:
        dest = DATA / "jobs" / f"{day}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        path.replace(dest)


def main() -> None:
    global DOCS
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    day = sys.argv[2] if len(sys.argv) > 2 else today_kst()
    inbox_file = INBOX / f"{day}.json"

    if cmd == "collect":
        collect()
    elif cmd == "check":
        errs = check(inbox_file)
        print("\n".join(errs) if errs else "OK: 모든 공고 분류 완료")
        sys.exit(1 if errs else 0)
    elif cmd == "build":
        build(inbox_file, day)
    elif cmd == "run":
        from .classify import classify
        path = collect()
        if not path:
            build_index(DOCS)
            return
        jobs = classify(read_jobs(path))
        write_jobs(path, jobs)
        if check(path):
            print("일부 공고 분류 실패 → inbox에 남겨둠")
            return
        build(path, day)
    elif cmd == "sample":
        from .classify import classify
        jobs = classify(read_jobs(ROOT / "tests" / "sample_jobs.json"))
        tmp = ROOT / "output" / "sample.json"
        write_jobs(tmp, jobs)
        DOCS = ROOT / "output" / "docs"
        DOCS.mkdir(parents=True, exist_ok=True)
        build(tmp, day, archive=False)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

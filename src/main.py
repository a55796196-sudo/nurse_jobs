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


POSTED_FILE = DATA / "posted.json"
CAPITAL = ("서울", "경기", "인천")


def load_posted() -> dict[str, str]:
    try:
        return json.loads(POSTED_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def mark_posted(jobs: list[Job], day: str) -> None:
    posted = load_posted()
    for j in jobs:
        posted.setdefault(j.key, day)
    POSTED_FILE.write_text(json.dumps(posted, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def open_targets(day: str, today_targets: list[Job]) -> list[Job]:
    """오늘 기준 마감 전인 탈임상 공고 전체 (지난 날짜 파일 + 오늘)."""
    out, keys = [], set()
    for j in today_targets + [j for f in sorted((DATA / "jobs").glob("*.json"), reverse=True) for j in read_jobs(f)]:
        if not j.is_target or j.key in keys or (j.deadline and j.deadline < day):
            continue
        keys.add(j.key)
        out.append(j)
    return out


def backlog(day: str) -> list[Job]:
    """아직 블로그에 안 올린, 마감 전(내일 이후) 탈임상 공고. 수도권 → 마감 빠른 순."""
    posted, seen_keys, out = load_posted(), set(), []
    files = sorted((DATA / "jobs").glob("*.json"), reverse=True)
    for f in files:
        for j in read_jobs(f):
            if not j.is_target or j.key in posted or j.key in seen_keys:
                continue
            if j.deadline and j.deadline <= day:
                continue
            seen_keys.add(j.key)
            out.append(j)
    out.sort(key=lambda j: (not any(c in (j.location or "") for c in CAPITAL), j.deadline or "9999"))
    return out


def read_jobs(path: Path) -> list[Job]:
    return [Job.from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))]


def write_jobs(path: Path, jobs: list[Job]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([j.to_dict() for j in jobs], ensure_ascii=False, indent=1), encoding="utf-8")


def collect() -> Path | None:
    today = today_kst()
    seen = load_seen()
    jobs: list[Job] = []
    from .sources import edu, gojobs
    for name, fn in (("alio", alio.fetch), ("saramin", saramin.fetch), ("edu", edu.fetch), ("gojobs", gojobs.fetch)):
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

    # 기관 채용 사이트에서 상세(보수·근무조건) 읽기 + 잡알리오에 없는 간호 공고 찾기
    try:
        from .sources import sites
        extra_jobs = sites.enrich(new_jobs, discover=True, seen=set(seen))
        extra_jobs = [j for j in extra_jobs if not (j.deadline and j.deadline < today)]
        new_jobs += extra_jobs
        print(f"채용 사이트에서 추가 발견 {len(extra_jobs)}건")
    except Exception as e:  # 사이트 읽기 실패해도 수집은 계속
        print(f"[sites] 전체 실패: {e}")

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
        elif j.blog_pick and not (j.is_target and (j.qualifications or j.requirements) and j.blog_comment and j.intro):
            errors.append(f"#{i} 블로그 글 필드(qualifications/blog_comment/intro) 비어있음: {j.title}")
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
        build_day(targets, d, DOCS, cards, all_open=open_targets(day, targets))
        print(f"완료: docs/{day}/index.html (카드 {len(cards)}장)")
    else:
        print("오늘은 탈임상 공고가 없어 페이지를 만들지 않습니다.")
    build_index(DOCS)
    if archive:
        mark_posted([j for j in targets if j.blog_pick], day)
        # 분류에 쓴 공고 이미지는 정리 (저장소 용량 관리)
        import shutil
        for j in jobs:
            shutil.rmtree(DATA / "assets" / f"{j.source}-{j.source_id}".replace(":", "-"), ignore_errors=True)
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
    elif cmd == "edutest":  # 디버그: 교육청 보건교사 수집 시험 + 경기 게시판 구조 확인
        from .sources import edu
        for j in edu.fetch():
            print("\n####", j.key, j.org, "|", j.title, "|", j.location, "|", j.start_date, "~", j.deadline, "|", j.employment_type)
            print("   ", {k: j.extra.get(k) for k in ("address", "recrutNope", "work_hours", "pay_type", "detail_url")})
            print("    본문:", (j.extra.get("site_text") or "")[:600])
    elif cmd == "gojobstest":  # 디버그: 나라일터 수집 시험
        from .sources import gojobs
        for j in gojobs.fetch(days=7):
            print("\n####", j.key, "|", j.org, "|", j.title, "|", j.location, "|", j.start_date, "~", j.deadline)
            print("    본문:", (j.extra.get("site_text") or "")[:700])
    elif cmd == "backlog":  # 대기열 보기: python -m src.main backlog [날짜]
        for j in backlog(day):
            print(f"{j.key} | {j.org} | {j.job_role or j.title[:30]} | {j.location} | ~{j.deadline}")
    elif cmd == "backlog-add":  # 대기열 공고를 그날 inbox 에 추가: python -m src.main backlog-add 날짜 KEY [KEY...]
        keys = set(sys.argv[3:])
        add = [j for j in backlog(day) if j.key in keys]
        for j in add:
            j.blog_pick = True
        cur = read_jobs(inbox_file) if inbox_file.exists() else []
        have = {j.key for j in cur}
        write_jobs(inbox_file, cur + [j for j in add if j.key not in have])
        print(f"{len(add)}건 추가 → {inbox_file} (blog_pick=true, intro·급여 등 블로그 필드를 채울 것)")
    elif cmd == "enrich":  # inbox 공고들의 채용사이트 상세를 다시 읽고, 미수집 공고를 최신 inbox에 추가
        from .sources import sites
        seen = load_seen()
        files = sorted(INBOX.glob("*.json"))
        all_jobs, by_file = [], {}
        for f in files:
            js = [j for j in read_jobs(f) if not (j.deadline and j.deadline < today_kst())]
            by_file[f] = js
            all_jobs += js
        found = sites.enrich(all_jobs, discover=True, seen=set(seen))
        found = [j for j in found if not (j.deadline and j.deadline < today_kst())]
        for j in found:
            seen[j.key] = today_kst()
        if files:
            by_file[files[-1]] += found
        for f, js in by_file.items():
            write_jobs(f, js) if js else f.unlink()
        save_seen(seen, today_kst())
        print(f"상세 읽기 완료: 기존 {len(all_jobs)}건, 새로 찾은 공고 {len(found)}건")
    elif cmd == "sitetest":  # 디버그: python -m src.main sitetest URL [URL...]
        from .sources import sites
        tests = [Job(source="test", source_id=str(i), title="", org="", url=u) for i, u in enumerate(sys.argv[2:])]
        found = sites.enrich(tests, discover=True)
        for j in tests + found[:3]:
            e = j.extra
            print("\n####", j.source, j.title or e.get("page_title"), e.get("detail_url"))
            print("본문:", (e.get("site_text") or "")[:1500])
            print("OCR:", (e.get("site_ocr") or "")[:2500])
            print("이미지:", e.get("site_images"))
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

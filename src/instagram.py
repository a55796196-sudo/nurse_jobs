"""인스타그램 게시물 업로드 - Instagram Graph API.

필요한 것 (GitHub Secrets / Variables):
  - IG_USER_ID      : 인스타 비즈니스(프로페셔널) 계정 ID
  - IG_ACCESS_TOKEN : 장기 액세스 토큰 (instagram_content_publish 권한)
        · "IG…"로 시작하는 토큰(인스타 로그인 방식) → graph.instagram.com
        · "EAA…"로 시작하는 토큰(페이스북 로그인 방식) → graph.facebook.com
  - PAGES_BASE_URL  : GitHub Pages 주소 (예: https://아이디.github.io/nurse_jobs)
이미지는 공개 URL이어야 하므로 GitHub Pages에 올라간 이미지를 사용합니다.

올릴 게시물:
  - 매일 피드: docs/YYYY-MM-DD/roundup-*.jpg (진행 중 공고 총정리) + roundup_caption.txt
  - 매일 스토리: docs/YYYY-MM-DD/story-NN.jpg (공고별, 캡션 없음)
  - 주간 가이드: docs/guides/YYYY-MM-DD/card-*.jpg + caption.txt
올린 기록: data/ig_posted.json  (같은 게시물을 두 번 올리지 않음)

사용법:
  python -m src.instagram next [--dry-run]       아직 안 올린 게시물 중 가장 오래된 1개 업로드 (예약 실행용)
  python -m src.instagram YYYY-MM-DD [--dry-run] 그날 게시물 전부 업로드
  python -m src.instagram guides/YYYY-MM-DD      가이드 카드뉴스 업로드
  python -m src.instagram status                 대기 중인 게시물 목록
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
POSTED = ROOT / "data" / "ig_posted.json"
COOLDOWN = ROOT / "data" / "ig_cooldown.json"   # 인스타 행동 차단 시 쉬는 기간
KST = timezone(timedelta(hours=9))
STORY_PER_RUN = 10  # 한 번 실행에 그날 스토리를 전부 올림 (사이사이 1.5~3분 간격)
MAX_AGE_DAYS = 2   # 이보다 오래된 날짜의 게시물은 예약 업로드에서 건너뜀 (D-day가 안 맞음)


def today_kst() -> date:
    return datetime.now(KST).date()


def _graph() -> str:
    tok = os.environ.get("IG_ACCESS_TOKEN", "")
    host = os.environ.get("IG_GRAPH_HOST") or ("graph.instagram.com" if tok.startswith("IG") else "graph.facebook.com")
    return f"https://{host}/{os.environ.get('IG_GRAPH_VERSION', 'v23.0')}"


# ---------- 게시물 목록 ----------
def _roundup_post(day: str) -> list[dict]:
    d = DOCS / day
    rc = sorted(d.glob("roundup-*.jpg"), key=lambda p: int(p.stem.split("-")[1]))
    if not rc:
        return []
    cap = (d / "roundup_caption.txt").read_text(encoding="utf-8") if (d / "roundup_caption.txt").exists() else ""
    return [{"id": f"{day}/roundup", "images": rc, "caption": cap}]


def _day_posts(day: str) -> list[dict]:
    """매일: 피드 = 진행 중 공고 총정리 카드(roundup-*.jpg) 1개, 스토리 = 공고별 story-NN.jpg."""
    d = DOCS / day
    out = []
    for p in sorted(d.glob("story-*.jpg")):
        out.append({"id": f"{day}/{p.stem}", "images": [p], "caption": "", "story": True})
    rc = sorted(d.glob("roundup-*.jpg"), key=lambda p: int(p.stem.split("-")[1]))
    # 총정리는 매일 피드에 올림 (한 번 실행에 피드는 1개씩이라 가이드 날도 따로 올라감)
    if rc:
        cap = (d / "roundup_caption.txt").read_text(encoding="utf-8") if (d / "roundup_caption.txt").exists() else ""
        out.append({"id": f"{day}/roundup", "images": rc, "caption": cap})
    return out


def _guide_posts(day: str) -> list[dict]:
    d = DOCS / "guides" / day
    imgs = sorted(d.glob("card-*.jpg"))
    if not imgs:
        return []
    cap = (d / "caption.txt").read_text(encoding="utf-8") if (d / "caption.txt").exists() else ""
    return [{"id": f"guides/{day}", "images": imgs, "caption": cap}]


def posts_for(target: str) -> list[dict]:
    if target.startswith("guides/"):
        return _guide_posts(target.split("/", 1)[1])
    if target.endswith("/roundup"):   # 요일과 상관없이 그날 총정리만
        return _roundup_post(target.split("/", 1)[0])
    return _day_posts(target)


def _posted() -> dict:
    try:
        return json.loads(POSTED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _mark(post_id: str, media_id: str) -> None:
    data = _posted()
    data[post_id] = {"media_id": media_id, "at": datetime.now(KST).isoformat(timespec="minutes")}
    POSTED.parent.mkdir(parents=True, exist_ok=True)
    POSTED.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def pending() -> list[dict]:
    """아직 안 올린 게시물 (최근 MAX_AGE_DAYS일, 가이드는 올릴 날짜가 된 것만, 마감 지난 공고 제외).
    오늘 것부터 → 어제 남은 것 순서."""
    done = _posted()
    today = today_kst()
    out = []
    for d in range(0, MAX_AGE_DAYS + 1):
        day = (today - timedelta(days=d)).isoformat()
        out += _guide_posts(day) if (DOCS / "guides" / day).is_dir() else []
        out += _day_posts(day) if (DOCS / day).is_dir() else []
    return [p for p in out if p["id"] not in done and not p.get("expired")]


# ---------- API ----------
def _post(path: str, **params) -> dict:
    import requests
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.post(f"{_graph()}/{path}", data=params, timeout=60)
    if r.status_code >= 400:
        if "request limit" in r.text or '"error_subcode":2207051' in r.text or '"code":4,' in r.text:
            # 앱 호출 한도 초과/행동 차단 → 6시간 쉬었다가 다시 시도 (한도는 보통 1시간 단위로 풀림)
            until = (datetime.now(KST) + timedelta(hours=6)).isoformat(timespec="minutes")
            COOLDOWN.write_text(json.dumps({"until": until, "why": r.text[:300]}, ensure_ascii=False), encoding="utf-8")
            print(f"인스타가 활동을 제한해 {until}까지 업로드를 쉽니다.")
            raise SystemExit(0)
        if "API access blocked" in r.text or '"code":190' in r.text:
            # 메타 계정·앱이 아직 막혀 있거나 토큰 만료 → 실패로 끝내지 않고 건너뜀 (매일 실패 알림 방지)
            print(f"인스타 API가 아직 막혀 있어 업로드를 건너뜁니다: {r.text[:200]}")
            raise SystemExit(0)
        raise RuntimeError(f"Instagram API 오류 {r.status_code}: {r.text[:500]}")
    return r.json()


def _wait_public(url: str, minutes: int = 15) -> None:
    """GitHub Pages 배포가 끝나 이미지가 공개될 때까지 대기."""
    import requests
    for _ in range(minutes * 6):
        if requests.head(url, timeout=15).status_code == 200:
            return
        time.sleep(10)
    raise RuntimeError(f"이미지가 아직 공개되지 않았습니다: {url}")


def _wait_container(cid: str) -> None:
    import requests
    time.sleep(10)
    for _ in range(30):   # 상태 확인도 API 호출 한도에 들어가므로 15초 간격으로
        r = requests.get(f"{_graph()}/{cid}", params={"fields": "status_code", "access_token": os.environ["IG_ACCESS_TOKEN"]}, timeout=30)
        status = r.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"미디어 처리 실패: {r.text[:300]}")
        time.sleep(15)
    raise RuntimeError(f"미디어 처리 시간 초과: {cid}")


def publish_one(post: dict, dry: bool = False) -> None:
    base = os.environ.get("PAGES_BASE_URL", "https://example.github.io/nurse_jobs").rstrip("/")
    urls = [f"{base}/{p.relative_to(DOCS).as_posix()}" for p in post["images"]][:10]
    if not post["caption"] and not post.get("story"):
        raise RuntimeError(f"{post['id']} 캡션이 비어 있습니다")
    print(f"▶ {post['id']} ({len(urls)}장)")
    if dry:
        print("\n".join("   " + u for u in urls))
        print("   " + post["caption"].replace("\n", "\n   "))
        return
    ig = os.environ["IG_USER_ID"]
    _wait_public(urls[-1])
    if post.get("story"):
        c = _post(f"{ig}/media", image_url=urls[0], media_type="STORIES")
    elif len(urls) == 1:
        c = _post(f"{ig}/media", image_url=urls[0], caption=post["caption"])
    else:
        children = [_post(f"{ig}/media", image_url=u, is_carousel_item="true")["id"] for u in urls]
        for cid in children:
            _wait_container(cid)
        c = _post(f"{ig}/media", media_type="CAROUSEL", children=",".join(children), caption=post["caption"])
    _wait_container(c["id"])
    try:
        res = _post(f"{ig}/media_publish", creation_id=c["id"])
    except RuntimeError:
        # 인스타가 '행동이 차단되었습니다' 오류를 주면서도 실제로는 게시하는 경우가 있음 → 컨테이너 상태로 확인
        import requests
        time.sleep(10)
        st = requests.get(f"{_graph()}/{c['id']}", params={"fields": "status_code", "access_token": os.environ["IG_ACCESS_TOKEN"]}, timeout=30).json().get("status_code")
        if st != "PUBLISHED":
            raise
        res = {"id": f"container:{c['id']}"}
        print("   (오류 응답을 받았지만 실제로는 게시됨)")
    _mark(post["id"], str(res.get("id")))
    print(f"   업로드 완료: media id {res.get('id')}")


def main(argv: list[str]) -> None:
    dry = "--dry-run" in argv
    args = [a for a in argv if not a.startswith("--")]
    target = args[0] if args else "next"

    if target == "status":
        for p in pending():
            print(f"{p['id']} ({len(p['images'])}장)")
        return
    if not dry:
        missing = [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "PAGES_BASE_URL") if not os.environ.get(k)]
        if missing:
            print(f"{', '.join(missing)} 가 설정되지 않아 인스타 업로드를 건너뜁니다.")
            return

    if target == "next":
        try:
            cd = json.loads(COOLDOWN.read_text(encoding="utf-8"))
            if cd.get("until", "") > datetime.now(KST).isoformat():
                print(f"인스타 제한으로 {cd['until']}까지 쉬는 중")
                return
        except (OSError, ValueError):
            pass
        # 계정 보호: 한 번 실행에 피드 최대 1개 + 스토리 최대 STORY_PER_RUN개, 사이사이 무작위 간격
        todo = pending()
        if not todo:
            print("올릴 게시물이 없습니다.")
            return
        stories = [p for p in todo if p.get("story") and p["id"].startswith(today_kst().isoformat())]
        feeds = [p for p in todo if not p.get("story")]
        batch = feeds[:1] + stories[:STORY_PER_RUN]
        for i, p in enumerate(batch):
            if i and not dry:
                time.sleep(random.randint(90, 180))
            publish_one(p, dry)
        print(f"남은 피드 {max(0, len(feeds) - 1)}개 / 남은 스토리 {max(0, len(stories) - STORY_PER_RUN)}개")
        return

    posts = posts_for(target)
    if not posts:
        sys.exit(f"{target} 에 올릴 이미지가 없습니다.")
    done = _posted()
    for i, p in enumerate(posts):
        if p["id"] in done and not dry:
            print(f"이미 올림: {p['id']}")
            continue
        publish_one(p, dry)
        if not dry and i < len(posts) - 1:
            time.sleep(random.randint(90, 180))   # 연속 업로드 간격


if __name__ == "__main__":
    main(sys.argv[1:])

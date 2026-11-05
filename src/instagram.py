"""인스타그램 카드뉴스(캐러셀) 업로드 - Instagram Graph API.

필요한 것:
  - 인스타 프로페셔널(비즈니스) 계정 + 연결된 페이스북 페이지
  - IG_USER_ID      : 인스타 비즈니스 계정 ID
  - IG_ACCESS_TOKEN : 장기 액세스 토큰 (instagram_content_publish 권한)
  - PAGES_BASE_URL  : GitHub Pages 주소 (예: https://아이디.github.io/nurse-jobs)
이미지는 공개 URL이어야 하므로 GitHub Pages에 올라간 카드를 사용합니다.

사용법: python -m src.instagram [YYYY-MM-DD]   (생략하면 오늘)
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
GRAPH = f"https://graph.facebook.com/{os.environ.get('IG_GRAPH_VERSION', 'v23.0')}"
KST = timezone(timedelta(hours=9))


def _post(path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.post(f"{GRAPH}/{path}", data=params, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Instagram API 오류 {r.status_code}: {r.text[:500]}")
    return r.json()


def _wait_public(url: str, minutes: int = 10) -> None:
    """GitHub Pages 배포가 끝나 이미지가 공개될 때까지 대기."""
    for _ in range(minutes * 6):
        if requests.head(url, timeout=15).status_code == 200:
            return
        time.sleep(10)
    raise RuntimeError(f"이미지가 아직 공개되지 않았습니다: {url}")


def _wait_container(cid: str) -> None:
    for _ in range(30):
        r = requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code", "access_token": os.environ["IG_ACCESS_TOKEN"]}, timeout=30)
        status = r.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"미디어 처리 실패: {r.text[:300]}")
        time.sleep(5)


def publish(day: str) -> None:
    for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "PAGES_BASE_URL"):
        if not os.environ.get(k):
            sys.exit(f"{k} 가 설정되지 않아 인스타 업로드를 건너뜁니다.")
    ig = os.environ["IG_USER_ID"]
    base = os.environ["PAGES_BASE_URL"].rstrip("/")
    day_dir = ROOT / "docs" / day
    cards = sorted(day_dir.glob("card-*.jpg"))
    if not cards:
        sys.exit(f"{day} 카드가 없습니다.")
    caption = (day_dir / "caption.txt").read_text(encoding="utf-8")

    urls = [f"{base}/{day}/{p.name}" for p in cards][:10]
    _wait_public(urls[-1])

    children = []
    for u in urls:
        c = _post(f"{ig}/media", image_url=u, is_carousel_item="true")
        children.append(c["id"])
    for cid in children:
        _wait_container(cid)
    carousel = _post(f"{ig}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)
    _wait_container(carousel["id"])
    res = _post(f"{ig}/media_publish", creation_id=carousel["id"])
    print(f"인스타 업로드 완료: media id {res.get('id')}")


if __name__ == "__main__":
    publish(sys.argv[1] if len(sys.argv) > 1 else datetime.now(KST).date().isoformat())

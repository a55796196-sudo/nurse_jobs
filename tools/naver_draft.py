"""네이버 블로그 임시저장 자동화 (노트북에서 실행).

작업실 페이지(GitHub Pages)의 [제목 복사]·[본문 복사] 버튼을 눌러 네이버 글쓰기에 붙여넣고
썸네일을 맨 위에 넣은 뒤 '저장'(임시저장)까지만 한다. 발행 버튼은 사람이 직접 누른다.

처음 한 번:
    pip install playwright
    python -m playwright install chromium        (크롬이 깔려 있으면 생략 가능)
    python naver_draft.py login             → 열린 창에서 네이버 로그인 ('로그인 상태 유지' 체크) 후 창 닫기

매일 (작업 스케줄러/launchd 로 예약하거나 직접):
    python tools/naver_draft.py                   어제·오늘 글(+그날 주말 가이드) 중 아직 안 한 것 전부 임시저장
    python tools/naver_draft.py 2026-11-20        특정 날짜
    python tools/naver_draft.py --only 1          글 1번만 (시험용)
    python tools/naver_draft.py --no-summary      전체 정리 글은 빼고 (기본: 함께 저장)
    python tools/naver_draft.py 2026-11-22 --redo 이미 임시저장한 날짜를 다시 저장 (글이 수정됐을 때)

설정 (환경변수 또는 아래 기본값):
    NAVER_BLOG_ID   네이버 블로그 아이디 (blog.naver.com/아이디)
    PAGES_BASE_URL  작업실 주소
"""
from __future__ import annotations

import json
import os
import random
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BLOG_ID = os.environ.get("NAVER_BLOG_ID", "live_in_fact")
PAGES = os.environ.get("PAGES_BASE_URL", "https://a55796196-sudo.github.io/nurse_jobs").rstrip("/")
HOME = Path.home() / ".nurse_jobs_naver"
PROFILE = HOME / "browser"
DONE = HOME / "drafted.json"
SHOTS = HOME / "screenshots"
KST = timezone(timedelta(hours=9))
MOD = "Meta" if sys.platform == "darwin" else "Control"


def log(msg: str) -> None:
    line = f"[{datetime.now(KST):%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    HOME.mkdir(parents=True, exist_ok=True)
    with open(HOME / "log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pause(a: float = 0.8, b: float = 1.8) -> None:
    time.sleep(random.uniform(a, b))


def _done() -> dict:
    try:
        return json.loads(DONE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _mark(key: str, title: str) -> None:
    d = _done()
    d[key] = {"title": title, "at": datetime.now(KST).isoformat(timespec="minutes")}
    DONE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def launch(p):
    PROFILE.mkdir(parents=True, exist_ok=True)
    kw = dict(user_data_dir=str(PROFILE), headless=False, viewport={"width": 1400, "height": 900},
              locale="ko-KR", permissions=["clipboard-read", "clipboard-write"])
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **kw)   # 설치된 크롬 사용
    except Exception:
        return p.chromium.launch_persistent_context(**kw)


# ---------- 네이버 에디터 ----------
def editor_frame(page):
    """에디터가 들어있는 프레임 (mainFrame iframe 이거나 페이지 자체)."""
    for _ in range(40):
        for fr in [page.main_frame, *page.frames]:
            try:
                if fr.locator(".se-documentTitle").count():
                    return fr
            except Exception:
                pass
        time.sleep(0.5)
    raise RuntimeError("글쓰기 에디터를 찾지 못했습니다 (로그인이 풀렸을 수 있어요: login 다시 실행)")


def close_popups(fr) -> None:
    # '작성 중인 글이 있습니다' → 취소 (이어쓰기 안 함), 도움말 패널 닫기
    for sel in (".se-popup-button-cancel", ".se-help-panel-close-button", "button.se-popup-close-button"):
        try:
            loc = fr.locator(sel)
            if loc.count() and loc.first.is_visible():
                loc.first.click()
                pause(0.5, 1)
        except Exception:
            pass


def open_writer(ctx):
    page = ctx.new_page()
    page.goto(f"https://blog.naver.com/{BLOG_ID}?Redirect=Write", wait_until="domcontentloaded")
    if "nid.naver.com" in page.url:
        raise RuntimeError("네이버 로그인이 필요합니다: python naver_draft.py login")
    fr = editor_frame(page)
    pause(2, 3)
    close_popups(fr)
    return page, fr


def insert_image(page, fr, path: Path) -> None:
    btn = fr.locator("button.se-image-toolbar-button, button[data-name='image']").first
    with page.expect_file_chooser(timeout=15000) as fc:
        btn.click()
    fc.value.set_files(str(path))
    # 업로드 끝날 때까지 대기
    for _ in range(60):
        if fr.locator(".se-component.se-image img").count():
            break
        time.sleep(0.5)
    pause(1.5, 2.5)


def save_draft(fr) -> None:
    for loc in (fr.get_by_role("button", name="저장", exact=True), fr.locator("button[class*='save_btn']")):
        try:
            if loc.count():
                loc.first.click()
                pause(2, 3)
                return
        except Exception:
            pass
    raise RuntimeError("'저장' 버튼을 찾지 못했습니다")


# ---------- 작업실 페이지 ----------
def copy_from_workroom(work, button_onclick: str) -> None:
    """작업실의 복사 버튼을 눌러 시스템 클립보드에 넣음 (사람이 누르는 것과 동일)."""
    work.bring_to_front()
    btn = work.locator(f"button[onclick=\"{button_onclick}\"]")
    btn.scroll_into_view_if_needed()
    btn.click()
    pause(0.6, 1.2)


def download(url: str) -> Path:
    tmp = Path(tempfile.gettempdir()) / ("nj_" + url.rsplit("/", 1)[-1])
    urllib.request.urlretrieve(url, tmp)
    return tmp


def draft_one(ctx, work, day: str, key: str, title_btn: str, body_btn: str, thumb: str) -> None:
    title = work.locator(f"#{title_btn.split(chr(39))[1]}").inner_text().strip()
    log(f"▶ {key}: {title}")
    page, fr = open_writer(ctx)
    try:
        # 1) 제목
        copy_from_workroom(work, title_btn)
        page.bring_to_front()
        fr.locator(".se-documentTitle .se-text-paragraph").first.click()
        pause()
        page.keyboard.press(f"{MOD}+V")
        pause()
        # 2) 본문 첫 줄로 이동 → 썸네일
        fr.locator(".se-component.se-text .se-text-paragraph").first.click()
        pause()
        insert_image(page, fr, download(f"{PAGES}/{day}/{thumb}"))
        # 3) 본문 붙여넣기 (이미지 아래)
        page.keyboard.press(f"{MOD}+End")
        page.keyboard.press("Enter")
        copy_from_workroom(work, body_btn)
        page.bring_to_front()
        pause()
        page.keyboard.press(f"{MOD}+V")
        pause(3, 5)
        # 4) 임시저장
        save_draft(fr)
        _mark(key, title)
        log(f"  임시저장 완료")
    except Exception:
        SHOTS.mkdir(parents=True, exist_ok=True)
        shot = SHOTS / f"{key.replace('/', '_')}_{datetime.now(KST):%H%M%S}.png"
        page.screenshot(path=str(shot))
        log(f"  실패 — 화면 저장: {shot}")
        raise
    finally:
        pause(1, 2)
        page.close()


def run(day: str, only: int | None, with_summary: bool, redo: bool = False) -> None:
    from playwright.sync_api import sync_playwright
    if not BLOG_ID:
        sys.exit("NAVER_BLOG_ID 환경변수에 블로그 아이디를 넣어주세요.")
    done = {} if redo else _done()   # --redo: 이미 임시저장한 글도 다시 저장
    # 서버 쪽 검토(ready.json)가 끝난 날만 저장. 아직이면 10분마다 확인하며 최대 3시간 기다림
    for k in range(19):
        try:
            with urllib.request.urlopen(f"{PAGES}/{day}/ready.json?t={int(time.time())}", timeout=20) as r:
                if r.status == 200:
                    break
        except Exception:  # noqa: BLE001
            pass
        if k == 0:
            log(f"{day} 아직 검토 전이라 기다립니다 (검토가 끝나면 자동으로 시작)")
        if k == 18:
            log(f"{day} 3시간 기다려도 검토가 끝나지 않아 건너뜁니다")
            return
        time.sleep(600)
    with sync_playwright() as p:
        ctx = launch(p)
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=PAGES.split("/nurse_jobs")[0])
        if not logged_in(ctx):
            ctx.close()
            sys.exit("네이버 로그인이 필요합니다: python naver_draft.py login")
        work = ctx.pages[0] if ctx.pages else ctx.new_page()
        ok = fail = 0
        # 1) 그날 공고 글  2) 그날 날짜의 주말 가이드 글 (미리 써둔 다음 주 가이드는 그 날짜가 되면 저장)
        for path in (day, f"guides/{day}"):
            if path.startswith("guides/") and only is not None:
                continue
            work.goto(f"{PAGES}/{path}/", wait_until="domcontentloaded")
            if work.locator("button[onclick^=\"copyText('pt\"]").count() == 0:
                if not path.startswith("guides/"):
                    log(f"{day} 작업실 페이지에 글이 없습니다 ({PAGES}/{path}/)")
                continue
            jobs = []
            if path.startswith("guides/"):
                jobs.append((path, "copyText('pt',this)", "copyHtml('pb',this)", "thumb.png"))
            else:
                n_posts = work.locator("button[onclick^=\"copyText('pt\"]").count()
                for n in range(1, n_posts + 1):
                    if only is None or only == n:
                        jobs.append((f"{day}/{n}", f"copyText('pt{n}',this)", f"copyHtml('pb{n}',this)", f"thumb-{n:02d}.png"))
                if with_summary and only is None:
                    jobs.append((f"{day}/summary", "copyText('st',this)", "copyHtml('sb',this)", "thumb-summary.png"))
            todo = [x for x in jobs if x[0] not in done]
            for x in jobs:
                if x[0] in done:
                    log(f"이미 임시저장함: {x[0]}")
            for i, (key, tb, bb, th) in enumerate(todo):
                if ok + fail:
                    log("  다음 글까지 대기…")
                    pause(20, 50)   # 글 사이 간격
                try:
                    draft_one(ctx, work, path, key, tb, bb, th)
                    ok += 1
                except Exception as e:
                    log(f"  오류: {e}")
                    fail += 1
        log(f"끝: 임시저장 {ok}개, 실패 {fail}개")
        ctx.close()


def logged_in(ctx) -> bool:
    names = {c["name"] for c in ctx.cookies("https://www.naver.com")}
    return {"NID_AUT", "NID_SES"} <= names


def login() -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if logged_in(ctx):
            print("이미 로그인되어 있습니다.")
        else:
            page.goto("https://nid.naver.com/nidlogin.login")
            print("열린 창에서 네이버에 로그인하세요 ('로그인 상태 유지' 체크). 창은 닫지 마세요 — 로그인되면 자동으로 닫힙니다.")
            for _ in range(600):          # 최대 10분 대기
                if logged_in(ctx):
                    break
                time.sleep(1)
            else:
                ctx.close()
                sys.exit("10분 안에 로그인이 확인되지 않았습니다. 다시 실행해 주세요.")
            print("로그인 확인! 저장 중...")
            page.goto("https://blog.naver.com/" + BLOG_ID, wait_until="domcontentloaded")
            time.sleep(5)                 # 쿠키가 디스크에 기록될 시간
        ctx.close()
        print("완료. 이제 임시저장을 실행하세요.")


def _main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "login":
        login()
    else:
        only = int(args[args.index("--only") + 1]) if "--only" in args else None
        pos = [a for a in args if not a.startswith("--") and not a.isdigit()]
        if pos:
            days = [pos[0]]
        else:   # 날짜를 안 주면 어제 + 오늘 (자정 실행 때 어제 글을 놓치지 않게)
            t = datetime.now(KST).date()
            days = [(t - timedelta(days=1)).isoformat(), t.isoformat()]
        for day in days:
            run(day, only, "--no-summary" not in args, "--redo" in args)


if __name__ == "__main__":
    import faulthandler
    import traceback
    HOME.mkdir(parents=True, exist_ok=True)
    _fh = open(HOME / "crash.txt", "a", encoding="utf-8")
    faulthandler.enable(_fh)          # 파이썬 자체가 죽어도 기록
    log(f"시작 (인자: {' '.join(sys.argv[1:]) or '없음'})")
    try:
        _main()
    except BaseException as e:        # noqa: BLE001
        log("비정상 종료:\n" + traceback.format_exc())
        raise

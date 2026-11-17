"""기관 채용 사이트(recruiter.co.kr 등)에서 공고 상세(근무조건·보수 등)를 읽어오고,
잡알리오에 없는 간호 공고(상시공고 등)를 찾아낸다.

- 신형 사이트(/career/jobs/ID): 본문이 이미지인 경우가 많음 → 이미지 저장 + OCR
- 구형 사이트(/app/jobnotice/view?...): 본문이 SmartEditor iframe 안에 있음 → 프레임 글자 읽기
GitHub Actions(국내 사이트 접속 가능)에서만 동작한다. Playwright·tesseract 필요.
"""
from __future__ import annotations

import io
import re
import subprocess
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from ..models import Job

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "data" / "assets"
NURSE = re.compile(r"간호|보건관리|연구원|코디네이터|CRC|CRA", re.I)
MAX_IMAGES = 6


def _home(url: str) -> str:
    u = urlparse(url)
    return f"{u.scheme}://{u.netloc}"


def _is_detail(url: str) -> bool:
    u = urlparse(url)
    return bool(re.search(r"/career/jobs/\d+", u.path) or "jobnoticeSn=" in u.query)


def _similar(a: str, b: str) -> float:
    norm = lambda s: re.sub(r"[\s\[\]()<>【】·,\-_/]", "", s)  # noqa: E731
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def _list_postings(page, home: str) -> list[tuple[str, str]]:
    """사이트의 공고 목록 → [(제목 텍스트, 상세 URL)]"""
    out: dict[str, str] = {}
    for path in ("/career/jobs", "/app/jobnotice/list"):
        try:
            page.goto(home + path, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1500)
        except Exception:  # noqa: BLE001
            continue
        for text, href in page.eval_on_selector_all(
            "a", "els => els.map(e => [e.innerText, e.href])"
        ):
            if href and _is_detail(href) and href.split("#")[0] not in out:
                out[href.split("#")[0]] = " ".join((text or "").split())
        if out:
            break
    return [(t, u) for u, t in out.items()]


def _clean_title(listing_text: str) -> str:
    t = re.sub(r"^(접수중|접수예정|상시)\s*", "", listing_text)
    t = re.split(r"\s+D-\d+|\s+D-DAY|\s+20\d\d\.\d\d\.\d\d", t)[0]
    return t.strip()


def _deadline_from_listing(text: str) -> str | None:
    dates = re.findall(r"(20\d\d)\.(\d\d)\.(\d\d)", text)
    if len(dates) >= 2:
        y, m, d = dates[-1]
        return f"{y}-{m}-{d}"
    return None


def _ocr(img_bytes: bytes) -> str:
    try:
        r = subprocess.run(["tesseract", "-", "-", "-l", "kor+eng", "--psm", "6"],
                           input=img_bytes, capture_output=True, timeout=120)
        return r.stdout.decode("utf8", "ignore")
    except Exception:  # noqa: BLE001
        return ""


def _save_image(img_bytes: bytes, path: Path) -> bool:
    """용량을 줄여 저장 (가로 1000px, 품질 70)."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        if im.width > 1000:
            im = im.resize((1000, round(im.height * 1000 / im.width)))
        path.parent.mkdir(parents=True, exist_ok=True)
        im.save(path, quality=70)
        return True
    except Exception:  # noqa: BLE001
        return False


def _read_detail(page, url: str, asset_key: str) -> dict:
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2000)
    texts = []
    for fr in page.frames:
        try:
            t = " ".join(fr.inner_text("body").split())
        except Exception:  # noqa: BLE001
            continue
        if t:
            texts.append(t)
    text = "\n".join(texts)
    host = urlparse(url).netloc
    imgs = page.eval_on_selector_all(
        "img", "els => els.map(e => [e.src, e.naturalWidth, e.naturalHeight])"
    )
    # 본문 이미지: 같은 사이트 업로드 경로, 가로 600px 이상 (로고·배너 제외)
    body_imgs = [s for s, w, h in imgs if s and w >= 600 and host in s and "/upload/" in s][:MAX_IMAGES]
    saved, ocr = [], []
    for i, src in enumerate(body_imgs, 1):
        try:
            b = requests.get(src, timeout=60).content
        except requests.RequestException:
            continue
        p = ASSETS / asset_key / f"{i}.jpg"
        if _save_image(b, p):
            saved.append(str(p.relative_to(ROOT)))
            ocr.append(_ocr(b))
    return {
        "detail_url": url,
        "page_title": page.title(),
        "site_text": text[:8000],
        "site_ocr": "\n".join(" ".join(o.split()) for o in ocr)[:12000],
        "site_images": saved,
    }


def enrich(jobs: list[Job], discover: bool = True, seen: set[str] | None = None) -> list[Job]:
    """jobs 의 상세를 채우고, 같은 사이트의 미수집 간호 공고를 새 Job 으로 돌려준다."""
    seen = seen or set()
    targets = [j for j in jobs if "recruiter.co.kr" in (j.url or "")]
    if not targets:
        return []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[sites] playwright 없음 → 건너뜀")
        return []

    found: list[Job] = []
    known_titles = [j.title for j in jobs]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        listings: dict[str, list[tuple[str, str]]] = {}
        for j in targets:
            home = _home(j.url)
            try:
                if home not in listings:
                    listings[home] = _list_postings(page, home)
                url = j.url
                if not _is_detail(url):
                    best = max(listings[home], key=lambda x: _similar(_clean_title(x[0]), j.title), default=None)
                    if best and _similar(_clean_title(best[0]), j.title) >= 0.6:
                        url = best[1]
                    else:
                        print(f"[sites] 상세 못 찾음: {j.title[:40]}")
                        continue
                j.extra.update(_read_detail(page, url, f"{j.source}-{j.source_id}"))
                print(f"[sites] 상세 OK: {j.org} {j.title[:30]} (이미지 {len(j.extra['site_images'])})")
            except Exception as e:  # noqa: BLE001
                print(f"[sites] 실패 {j.url}: {e}")

        if discover:
            for home, items in listings.items():
                org = next((j.org for j in targets if _home(j.url) == home), urlparse(home).netloc)
                for text, url in items:
                    title = _clean_title(text)
                    sid = f"{urlparse(home).netloc}:{re.findall(r'\d+', urlparse(url).path + urlparse(url).query)[-1]}"
                    if not NURSE.search(title) or f"site:{sid}" in seen:
                        continue
                    if any(_similar(title, t) >= 0.6 for t in known_titles):
                        continue
                    job = Job(source="site", source_id=sid, title=title, org=org, url=url,
                              deadline=_deadline_from_listing(text))
                    try:
                        job.extra.update(_read_detail(page, url, f"site-{sid.replace(':', '-')}"))
                        job.raw_text = (title + " " + job.extra.get("site_text", "") + " " + job.extra.get("site_ocr", ""))[:3000]
                    except Exception as e:  # noqa: BLE001
                        print(f"[sites] 신규 상세 실패 {url}: {e}")
                        job.raw_text = title
                    found.append(job)
                    known_titles.append(title)
                    print(f"[sites] 잡알리오에 없는 공고 발견: {org} {title[:40]}")
        browser.close()
    return found

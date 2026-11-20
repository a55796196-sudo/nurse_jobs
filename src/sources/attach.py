"""공고 첨부파일(hwp·hwpx·pdf·docx·zip·이미지)을 내려받아 글자를 뽑는다.

분류 중 블로그 글로 고른 공고만 대상 (python -m src.main attach YYYY-MM-DD).
GitHub Actions(국내 사이트 접속 가능)에서 실행. 필요: playwright, olefile, poppler-utils, tesseract.
결과: job.extra["attach_files"] (읽은 파일 이름), job.extra["attach_text"] (본문, 최대 MAX_TEXT자)
"""
from __future__ import annotations

import html
import io
import re
import subprocess
import tempfile
import zipfile
import zlib
from pathlib import Path

MAX_FILES = 3
MAX_TEXT = 8000
MAX_BYTES = 15 * 1024 * 1024
EXT = re.compile(r"\.(hwpx?|pdf|docx|zip|jpe?g|png)\b", re.I)
# 지원서·서식류는 건너뜀 (공고문·직무기술서만)
SKIP = re.compile(r"지원서|입사지원|서식|양식|동의서|자기소개|이의신청|반환청구|확인서|서약서|신청서|위임장|증명서|체크리스트")
PRIORITY = (re.compile(r"공고"), re.compile(r"직무기술|직무설명"), re.compile(r"채용|모집|안내"))
KEYWORDS = re.compile(r"보수|급여|임금|연봉|월급|기본급|수당|근무\s*(시간|형태|일|조건|장소|지)|자격|요건|우대|가산|전형|절차|"
                      r"접수|모집\s*(인원|분야)|채용\s*인원|계약\s*기간|직무|업무|담당|복리|후생|제출\s*서류")


# ---------- 파일 → 글자 ----------
def _hwp(data: bytes) -> str:
    import olefile
    ole = olefile.OleFileIO(io.BytesIO(data))
    flags = int.from_bytes(ole.openstream("FileHeader").read()[36:40], "little")
    compressed, encrypted, distributed = flags & 1, flags & 2, flags & 4
    if encrypted or distributed:   # 암호·배포용 문서 → 미리보기 글자만
        return ole.openstream("PrvText").read().decode("utf-16le", "ignore") if ole.exists("PrvText") else ""
    out = []
    sections = sorted((s for s in ole.listdir() if s[0] == "BodyText"), key=lambda s: int(re.sub(r"\D", "", s[1]) or 0))
    for s in sections:
        raw = ole.openstream(s).read()
        if compressed:
            raw = zlib.decompress(raw, -15)
        i = 0
        while i + 4 <= len(raw):
            h = int.from_bytes(raw[i:i + 4], "little")
            tag, size = h & 0x3FF, (h >> 20) & 0xFFF
            i += 4
            if size == 0xFFF:
                size = int.from_bytes(raw[i:i + 4], "little")
                i += 4
            if tag == 67:   # HWPTAG_PARA_TEXT
                out.append(_para(raw[i:i + size]))
            i += size
    return "\n".join(out)


def _para(b: bytes) -> str:
    s, j, n = [], 0, len(b) // 2
    while j < n:
        c = int.from_bytes(b[j * 2:j * 2 + 2], "little")
        if c in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23):
            if c == 9:
                s.append("\t")
            j += 8          # 확장·인라인 컨트롤은 8글자 차지
            continue
        if c in (10, 13):
            s.append("\n" if c == 10 else "")
        elif c >= 32:
            s.append(chr(c))
        j += 1
    return "".join(s)


def _xml_text(xml: str, para_end: str) -> str:
    xml = xml.replace(para_end, "\n").replace("</hp:tc>", " | ").replace("</w:tc>", " | ")
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def _hwpx(data: bytes) -> str:
    z = zipfile.ZipFile(io.BytesIO(data))
    names = sorted((n for n in z.namelist() if re.match(r"Contents/section\d+\.xml", n)),
                   key=lambda n: int(re.sub(r"\D", "", n)))
    return "\n".join(_xml_text(z.read(n).decode("utf-8", "ignore"), "</hp:p>") for n in names)


def _docx(data: bytes) -> str:
    z = zipfile.ZipFile(io.BytesIO(data))
    return _xml_text(z.read("word/document.xml").decode("utf-8", "ignore"), "</w:p>")


def _ocr_image(data: bytes) -> str:
    r = subprocess.run(["tesseract", "-", "-", "-l", "kor+eng", "--psm", "6"], input=data, capture_output=True, timeout=180)
    return r.stdout.decode("utf-8", "ignore")


def _pdf(data: bytes) -> str:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.pdf"
        p.write_bytes(data)
        r = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, timeout=120)
        text = r.stdout.decode("utf-8", "ignore")
        if len(text.strip()) >= 200:
            return text
        # 스캔본 → 앞 4쪽만 글자인식
        subprocess.run(["pdftoppm", "-r", "150", "-l", "4", "-png", str(p), str(Path(d) / "pg")], timeout=180)
        return "\n".join(_ocr_image(x.read_bytes()) for x in sorted(Path(d).glob("pg*.png")))


def _zip(data: bytes, depth: int = 0) -> list[tuple[str, str]]:
    out = []
    z = zipfile.ZipFile(io.BytesIO(data))
    for info in z.infolist():
        name = info.filename
        if not info.flag_bits & 0x800:   # 한글 파일 이름(cp949) 복원
            try:
                name = name.encode("cp437").decode("cp949")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        base = name.rsplit("/", 1)[-1]
        if info.is_dir() or not EXT.search(base) or SKIP.search(base) or info.file_size > MAX_BYTES:
            continue
        out += extract(base, z.read(info), depth + 1)
    return out


def extract(name: str, data: bytes, depth: int = 0) -> list[tuple[str, str]]:
    """[(파일 이름, 글자)] — zip 이면 안의 파일들."""
    ext = (EXT.search(name) or re.search(r"$", "")).group(0).lower().lstrip(".")
    # 이름보다 실제 내용으로 판단 (확장자가 틀린 파일이 많음)
    if data[:4] == b"%PDF":
        ext = "pdf"
    elif data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        ext = "hwp"
    elif data[:2] == b"PK":
        ext = "zip"
    elif data[:3] == b"\xff\xd8\xff":
        ext = "jpg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        ext = "png"
    elif data.lstrip()[:1] == b"<":
        print(f"[attach] {name}: 파일이 아니라 웹페이지가 받아짐 ({data[:120]!r})")
        return []
    try:
        if ext == "zip":
            if depth > 1:
                return []
            try:   # hwpx·docx 도 zip 형식
                names = zipfile.ZipFile(io.BytesIO(data)).namelist()
            except zipfile.BadZipFile:
                return []
            if any(n.startswith("Contents/section") for n in names):
                return [(name, _hwpx(data))]
            return _zip(data, depth)
        fn = {"hwp": _hwp, "hwpx": _hwpx, "pdf": _pdf, "docx": _docx, "jpg": _ocr_image, "jpeg": _ocr_image, "png": _ocr_image}.get(ext)
        return [(name, fn(data))] if fn else []
    except Exception as e:  # noqa: BLE001
        print(f"[attach] 읽기 실패 {name}: {e}")
        return []


# ---------- 글자 정리 ----------
def tidy(text: str) -> str:
    lines = [" ".join(ln.split()) for ln in text.splitlines()]
    out, prev = [], None
    for ln in lines:
        if ln and ln != prev:
            out.append(ln)
        prev = ln
    return "\n".join(out)


def excerpt(text: str, limit: int = MAX_TEXT) -> str:
    """길면 급여·근무·자격·우대·전형 등 핵심 줄(+뒤 4줄)만 남김."""
    if len(text) <= limit:
        return text
    lines = text.splitlines()
    keep: set[int] = set()
    for i, ln in enumerate(lines):
        if KEYWORDS.search(ln):
            keep.update(range(i, min(i + 5, len(lines))))
    picked = "\n".join(lines[i] for i in sorted(keep)) or text
    return picked[:limit]


def choose(names: list[str]) -> list[str]:
    """공고문 → 직무기술서 → 기타 순으로 최대 MAX_FILES 개 (서식·지원서 제외)."""
    cand = [n for n in names if not SKIP.search(n)]
    rank = lambda n: next((i for i, p in enumerate(PRIORITY) if p.search(n)), len(PRIORITY))  # noqa: E731
    return sorted(cand, key=rank)[:MAX_FILES]


# ---------- 공고 페이지에서 내려받기 ----------
def download_from_page(page, url: str, want: list[str] | None = None) -> list[tuple[str, bytes]]:
    """상세 페이지의 첨부 링크를 눌러 내려받음 (사람이 클릭하는 것과 같음)."""
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    links = []
    for fr in page.frames:
        try:
            for el in fr.query_selector_all("a, button"):
                label = " ".join(((el.inner_text() or "") + " " + (el.get_attribute("title") or "")).split())
                href = el.get_attribute("href") or ""
                onclick = el.get_attribute("onclick") or ""
                if EXT.search(label) or EXT.search(href) or re.search(r"down|atchFile|fileId|FileDown", href + onclick, re.I):
                    links.append((label or href, el))
        except Exception:  # noqa: BLE001
            continue
    labels = [lb for lb, _ in links]
    chosen = choose([lb for lb in labels if EXT.search(lb)] or labels)
    if want:   # API 가 알려준 파일 이름과 맞는 링크를 우선
        named = [lb for lb in labels if any(w[:15] in lb for w in want if not SKIP.search(w))]
        chosen = choose(named) or chosen
    uniq: dict[str, object] = {}
    for lb, el in links:   # 같은 이름의 링크(PC·모바일용 등)는 보이는 것 하나만
        try:
            vis = el.is_visible()
        except Exception:  # noqa: BLE001
            vis = False
        if lb not in uniq or vis:
            uniq[lb] = (el, vis)
    out = []
    for lb, (el, vis) in uniq.items():
        if lb not in chosen or len(out) >= MAX_FILES:
            continue
        try:
            with page.expect_download(timeout=30000) as dl:
                if vis:
                    el.click()
                else:
                    el.evaluate("e => e.click()")
            d = dl.value
            data = Path(d.path()).read_bytes()
            name = d.suggested_filename or lb
            if SKIP.search(name):
                continue
            if len(data) <= MAX_BYTES:
                out.append((name, data))
        except Exception as e:  # noqa: BLE001
            print(f"[attach] 내려받기 실패 '{lb[:40]}': {e}")
    print(f"[attach] {url} → 링크 {len(links)}개 중 {len(out)}개 받음")
    return out


def page_url(job) -> str | None:
    e = job.extra or {}
    if job.source == "alio":
        return e.get("alio_url") or f"https://job.alio.go.kr/recruitview.do?idx={job.source_id}"
    if job.source in ("gojobs", "sen", "site"):
        return e.get("detail_url") or job.url
    if job.source == "saramin":
        return job.url
    return None   # goe 등 목록 페이지뿐인 출처


def enrich(jobs: list) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(accept_downloads=True, locale="ko-KR")
        page = ctx.new_page()
        for j in jobs:
            url = page_url(j)
            if not url:
                print(f"[attach] 페이지 없음: {j.title[:40]}")
                continue
            try:
                files = download_from_page(page, url, want=j.extra.get("files"))
            except Exception as e:  # noqa: BLE001
                print(f"[attach] 페이지 실패 {url}: {e}")
                continue
            texts = []
            for name, data in files:
                for n, t in extract(name, data):
                    t = tidy(t)
                    if t:
                        texts.append((n, t))
            if not texts:
                continue
            j.extra["attach_files"] = [n for n, _ in texts]
            j.extra["attach_text"] = excerpt("\n\n".join(f"[{n}]\n{t}" for n, t in texts))
            print(f"[attach] OK {j.org} {j.title[:30]}: {len(j.extra['attach_text'])}자 ({', '.join(j.extra['attach_files'])})")
        b.close()

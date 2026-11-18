"""인스타그램 카드뉴스 이미지 생성 (1080x1350, 4:5 비율).

카드 구성: 표지 1장 + 공고 카드 최대 8장 + 전체 정리 1장 (인스타 캐러셀 최대 10장)
폰트: fonts/ 폴더의 Pretendard (SIL OFL 1.1)
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import CATEGORIES, Job

W, H = 1080, 1350
PAD = 80
FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"

BRAND = os.environ.get("BRAND_NAME") or "탈임상 채용노트"
HANDLE = os.environ.get("IG_HANDLE", "")

# 색상: 크림 바탕 + 검정 글자 + 노란 형광펜
BG = "#FFFCF3"
INK = "#111111"
SUB = "#4A4A4A"
MUTED = "#9B988F"
LINE = "#E8E3D3"
MARK = "#FFE24D"   # 형광펜
RED = "#F03E3E"    # 마감 임박

CAT_LABEL = {"공공": "공공기관", "학교": "학교", "기업": "기업", "연구": "연구"}

_cache: dict = {}


def font(size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    k = (size, weight)
    if k not in _cache:
        name = "BlackHanSans-Regular.ttf" if weight == "Title" else f"Pretendard-{weight}.otf"
        path = FONT_DIR / name
        _cache[k] = ImageFont.truetype(str(path), size)
    return _cache[k]


def wrap(draw: ImageDraw.ImageDraw, text: str, f, max_w: int, max_lines: int) -> list[str]:
    """공백 기준 줄바꿈, 너무 긴 단어는 글자 단위. 넘치면 말줄임표."""
    text = " ".join((text or "").split())
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=f) <= max_w:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = ""
        for ch in w:  # 단어 자체가 너무 길면 글자 단위로
            if draw.textlength(cur + ch, font=f) <= max_w:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=f) > max_w:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def d_day(deadline: str | None, today: date) -> str:
    """블로그·캡션용 마감 표기. 예: 'D-4 · 11/9 마감'"""
    label, dl = d_label(deadline, today)
    if dl is None:
        return label if deadline is None or label != deadline else deadline
    return f"{label} · {dl.month}/{dl.day} 마감"


def d_label(deadline: str | None, today: date) -> tuple[str, date | None]:
    if not deadline:
        return "상시채용", None
    try:
        dl = date.fromisoformat(deadline)
    except ValueError:
        return deadline, None
    n = (dl - today).days
    return ("D-DAY" if n == 0 else f"D-{n}" if n > 0 else "마감"), dl


# ---------- 그리기 도우미 ----------

def _header(d: ImageDraw.ImageDraw, left: str, right: str):
    d.text((PAD, 90), left, font=font(30, "SemiBold"), fill=MUTED, anchor="lm")
    d.text((W - PAD, 90), right, font=font(30, "SemiBold"), fill=MUTED, anchor="rm")


def _marked(d: ImageDraw.ImageDraw, x, y, text, f, fill=INK):
    """형광펜 칠한 제목 한 줄."""
    bb = d.textbbox((x, y), text, font=f)
    h = bb[3] - bb[1]
    d.rectangle([bb[0] - 10, bb[3] - h * 0.42, bb[2] + 10, bb[3] + 10], fill=MARK)
    d.text((x, y), text, font=f, fill=fill)


def _short_loc(loc: str | None) -> str:
    if not loc:
        return "공고 참고"
    parts = [x.strip() for x in loc.replace(">", " ").split(",") if x.strip()]
    if not parts:
        return "공고 참고"
    return parts[0][:10] + (f" 외 {len(parts) - 1}곳" if len(parts) > 1 else "")


def _is_urgent(label: str) -> bool:
    return label == "D-DAY" or (label.startswith("D-") and label[2:].isdigit() and int(label[2:]) <= 3)


# ---------- 카드 ----------

def cover(jobs: list[Job], today: date, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _header(d, BRAND, f"{today.month}.{today.day:02d}")

    t = font(128, "Title")
    d.text((PAD, 250), "오늘의", font=t, fill=INK)
    _marked(d, PAD, 400, "탈임상 공고", t)

    num = f"{len(jobs)}건"
    d.text((PAD, 590), num, font=font(250, "Title"), fill=INK)

    counts = [f"{c} {sum(1 for j in jobs if j.category == c)}" for c in CATEGORIES if any(j.category == c for j in jobs)]
    d.text((PAD, 900), "  ·  ".join(counts), font=font(42, "Bold"), fill=SUB)

    orgs = []
    for j in jobs:
        o = j.org.replace("(주)", "").strip()
        if o not in orgs:
            orgs.append(o)
    preview = ", ".join(orgs[:3]) + (" 외" if len(orgs) > 3 else "")
    for i, line in enumerate(wrap(d, preview, font(34, "Medium"), W - PAD * 2, 2)):
        d.text((PAD, 975 + i * 50), line, font=font(34, "Medium"), fill=MUTED)

    d.text((PAD, H - 100), "넘겨서 확인하기 →", font=font(36, "Bold"), fill=INK, anchor="lm")
    return img


def job_card(job: Job, today: date, idx: int, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _header(d, f"{idx - 1:02d}  {CAT_LABEL.get(job.category or '', '기타')}", f"{idx} / {total}")

    # 기관명 + 직무명(형광펜)
    y = 190
    t = font(92, "Title")
    for line in wrap(d, job.org.replace("(주)", "").strip(), t, W - PAD * 2, 2):
        d.text((PAD, y), line, font=t, fill=INK)
        y += 118
    role_lines = wrap(d, job.job_role or job.title, t, W - PAD * 2 - 20, 2)
    for line in role_lines:
        _marked(d, PAD, y, line, t)
        y += 118

    # 마감
    y += 30
    label, dl = d_label(job.deadline, today)
    dtxt = label + (f"  ·  {dl.month}월 {dl.day}일 마감" if dl else "")
    d.text((PAD, y), dtxt, font=font(44, "ExtraBold"), fill=RED if _is_urgent(label) else INK)
    y += 90

    # 근무지 / 고용형태
    for k, v in (("근무지", _short_loc(job.location)), ("고용형태", (job.employment_type or "공고 참고").split(",")[0])):
        d.text((PAD, y), k, font=font(36, "Medium"), fill=MUTED)
        d.text((PAD + 190, y), v, font=font(36, "SemiBold"), fill=INK)
        y += 60

    d.line([(PAD, y + 30), (W - PAD, y + 30)], fill=LINE, width=3)
    y += 75

    # 요약 + 지원 자격 (남은 공간에 맞춰 줄 수 조절)
    bottom = H - 150
    reqs = job.requirements[:3]
    req_h = lambda n: (60 + 56 * n) if n else 0  # noqa: E731
    while reqs and y + 2 * 54 + 30 + req_h(len(reqs)) > bottom:
        reqs = reqs[:-1]
    sum_f = font(35, "Regular")
    max_lines = max(1, min(4, (bottom - y - 30 - req_h(len(reqs))) // 54))
    for line in wrap(d, job.summary or "", sum_f, W - PAD * 2, max_lines):
        d.text((PAD, y), line, font=sum_f, fill=SUB)
        y += 54
    if reqs:
        y += 30
        d.text((PAD, y), "지원 자격", font=font(34, "Bold"), fill=INK)
        y += 60
        for r in reqs:
            d.text((PAD, y), "·", font=font(36, "Bold"), fill=INK)
            d.text((PAD + 30, y), wrap(d, r, font(34, "Medium"), W - PAD * 2 - 30, 1)[0], font=font(34, "Medium"), fill=SUB)
            y += 56

    d.text((W / 2, H - 80), "원문 링크는 프로필에서 확인하세요", font=font(28, "Medium"), fill=MUTED, anchor="mm")
    return img


def summary(jobs: list[Job], today: date, total: int) -> Image.Image:
    """마지막 장: 전체 공고 한눈에 정리 (마감 빠른 순)."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _header(d, BRAND, f"{total} / {total}")
    _marked(d, PAD, 160, "한눈에 정리", font(96, "Title"))

    rows = sorted(jobs, key=lambda j: j.deadline or "9999")
    top, bottom = 330, H - 200
    max_rows = 18
    extra = 0
    if len(rows) > max_rows:
        extra = len(rows) - (max_rows - 1)
        rows = rows[: max_rows - 1]
    n = len(rows) + (1 if extra else 0)
    row_h = min(92, (bottom - top) / max(n, 1))
    fs = max(26, min(36, int(row_h * 0.46)))
    f_d, f_org, f_role, f_date = font(fs, "ExtraBold"), font(fs, "Bold"), font(fs, "Medium"), font(fs, "SemiBold")
    d_w = d.textlength("D-DAY", font=f_d) + 28
    date_w = d.textlength("12/31", font=f_date)

    y = top
    for j in rows:
        label, dl = d_label(j.deadline, today)
        cy = y + row_h / 2
        d.text((PAD, cy), label if dl else "상시", font=f_d, fill=RED if _is_urgent(label) else INK, anchor="lm")
        org = j.org.replace("(주)", "").strip()
        x = PAD + d_w
        room = W - PAD - date_w - 30 - x
        org_txt = wrap(d, org, f_org, room * 0.62, 1)[0]
        d.text((x, cy), org_txt, font=f_org, fill=INK, anchor="lm")
        x2 = x + d.textlength(org_txt, font=f_org) + 16
        if j.job_role and room - (x2 - x) > 60:
            d.text((x2, cy), wrap(d, j.job_role, f_role, room - (x2 - x), 1)[0], font=f_role, fill=MUTED, anchor="lm")
        if dl:
            d.text((W - PAD, cy), f"{dl.month}/{dl.day}", font=f_date, fill=SUB, anchor="rm")
        y += row_h
        d.line([(PAD, y), (W - PAD, y)], fill=LINE, width=2)
    if extra:
        d.text((PAD, y + row_h / 2), f"외 {extra}건은 블로그에서 확인하세요", font=f_role, fill=MUTED, anchor="lm")

    d.text((PAD, H - 140), "저장해두고 마감 놓치지 마세요", font=font(40, "Title"), fill=INK, anchor="lm")
    d.text((PAD, H - 82), "원문 링크는 프로필에서" + (f"  ·  @{HANDLE}" if HANDLE else ""), font=font(30, "Medium"), fill=MUTED, anchor="lm")
    return img


def render_all(jobs: list[Job], today: date, out_dir: Path, limit: int = 8) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # 카테고리별로 번갈아 뽑아 한 분야만 카드를 차지하지 않게 함 (마감 빠른 순 유지)
    queues = {c: [j for j in jobs if j.category == c] for c in CATEGORIES}
    picked: list[Job] = []
    while len(picked) < limit and any(queues.values()):
        for c in CATEGORIES:
            if queues[c] and len(picked) < limit:
                picked.append(queues[c].pop(0))
    order = list(CATEGORIES)
    picked.sort(key=lambda j: (order.index(j.category), j.deadline or "9999"))

    total = len(picked) + 2
    images = [cover(jobs, today, total)]
    images += [job_card(j, today, i, total) for i, j in enumerate(picked, start=2)]
    images.append(summary(jobs, today, total))
    paths = []
    for i, im in enumerate(images):
        p = out_dir / f"card-{i:02d}.jpg"
        im.save(p, quality=93)
        paths.append(p)
    return paths


# ---------- 블로그 썸네일 (1080x1080): 기관·직무·마감·근무지·고용형태만 ----------
WEEK = "월화수목금토일"


def thumb(org: str, role: str, deadline: str | None, deadline_time: str | None, loc: str, emp: str) -> Image.Image:
    S, P = 1080, 90
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)
    for size in (100, 90, 80, 72, 64):
        t = font(size, "Title")
        org_l = wrap(d, org, t, S - P * 2, 2)
        role_l = wrap(d, role, t, S - P * 2 - 20, 2)
        if len(org_l) + len(role_l) <= 4 and not any(x.endswith("…") for x in org_l + role_l):
            break
    y, lh = 130, int(size * 1.28)
    for x in org_l:
        d.text((P, y), x, font=t, fill=INK)
        y += lh
    for x in role_l:
        _marked(d, P, y, x, t)
        y += lh
    if deadline:
        dt = date.fromisoformat(deadline)
        dl = f"{dt.month}.{dt.day} ({WEEK[dt.weekday()]})" + (f" {deadline_time}" if deadline_time else "")
    else:
        dl = "상시 (채용 시 마감)"
    rows = [("마감", dl, RED), ("근무지", loc, INK), ("고용형태", emp, INK)]
    y = S - 130 - 3 * 92
    d.line([(P, y - 40), (S - P, y - 40)], fill=LINE, width=3)
    for k, v, c in rows:
        d.text((P, y + 34), k, font=font(38, "Medium"), fill=MUTED, anchor="lm")
        d.text((P + 220, y + 34), wrap(d, v, font(48, "Bold"), S - P * 2 - 220, 1)[0], font=font(48, "Bold"), fill=c, anchor="lm")
        y += 92
    return img


def summary_thumb(today: date, total: int, counts: list[tuple[str, int]], soon: int) -> Image.Image:
    """'전체 공고 정리' 글 썸네일."""
    S, P = 1080, 90
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)
    t = font(100, "Title")
    d.text((P, 130), f"{today.month}월 {today.day}일", font=t, fill=INK)
    d.text((P, 258), "탈임상 채용공고", font=t, fill=INK)
    _marked(d, P, 386, "총정리", t)
    rows = [("진행 중", f"{total}건", INK), ("분야", "  ".join(f"{k} {v}" for k, v in counts if v) or "-", INK),
            ("마감 임박", f"3일 이내 {soon}건", RED)]
    y = S - 130 - 3 * 92
    d.line([(P, y - 40), (S - P, y - 40)], fill=LINE, width=3)
    for k, v, c in rows:
        d.text((P, y + 34), k, font=font(38, "Medium"), fill=MUTED, anchor="lm")
        d.text((P + 220, y + 34), v, font=font(48, "Bold"), fill=c, anchor="lm")
        y += 92
    return img


# ---------- 인스타 게시물 (공고 1개 = 1장, 1080x1350): 파스텔 + 형광펜 ----------
# (배경, 형광펜·장식, 포인트색, 칩 이름) — 주로 나오는 기업·공공이 분홍·노랑
IG_PAL = {
    "기업": ("#FDE1E4", "#FFC2CB", "#E0556D", "기업"),
    "공공": ("#FFF1C9", "#FFE07A", "#E08A1E", "공공기관"),
    "연구": ("#DCEEFB", "#B3DAF7", "#2F86C8", "임상연구"),
    "학교": ("#DDF0E6", "#B8E6CF", "#2E9E6E", "학교 보건실"),
    "기타": ("#E6E3FA", "#CFC7FF", "#6C5CE0", "기타"),
}
IG_SOURCE = {"alio": "잡알리오", "sen": "서울시교육청 교육일자리포털", "goe": "경기도교육청 구인정보",
             "gojobs": "나라일터", "site": "기관 채용 홈페이지", "saramin": "사람인"}


def _sparkle(d: ImageDraw.ImageDraw, x: float, y: float, r: float, col: str) -> None:
    import math
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.32
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=col)


def ig_post(job: Job, today: date, h: int = H) -> Image.Image:
    """h=1350 인스타 표지, h=1080 블로그 썸네일(정사각형)."""
    sq = h < H
    from .blog import _emp, _org  # 순환 import 방지
    bg, mark, pt, lab = IG_PAL.get(job.category or "기타", IG_PAL["기타"])
    role = job.job_role or ""
    emp = "" if "강사" in role else _emp(job)
    segs = [_org(job), job.department or "", " ".join(f"{role} {emp if emp not in role else ''} 채용".split())]
    segs = [s for s in segs if s]
    dl = date.fromisoformat(job.deadline) if job.deadline else None
    left = (dl - today).days if dl else None
    when = f"~{dl.month}/{dl.day}({WEEK[dl.weekday()]})" if dl else "상시 채용"
    dd = ("D-DAY" if left == 0 else f"D-{left}") if dl else "상시"
    loc = (job.location or "").split(",")[0].replace("특별시", "").replace("광역시", "").strip()

    img = Image.new("RGB", (W, h), bg)
    d = ImageDraw.Draw(img)
    for i in range(0, W + 80, 120):  # 물방울 무늬
        for j in range(0, h + 80, 120):
            if (i // 120 + j // 120) % 2 == 0:
                d.ellipse((i - 7, j - 7, i + 7, j + 7), fill=mark)
    x0, y0, x1, y1 = (80, 100, W - 80, h - 130) if sq else (80, 150, W - 80, H - 150)
    d.rounded_rectangle((x0, y0 + 12, x1, y1 + 12), 56, fill=mark)
    d.rounded_rectangle((x0, y0, x1, y1), 56, fill="white")
    # 칩: 카테고리 / 지역
    f = font(38, "Bold")
    cx = x0 + 70
    for txt, fill, col in ((lab, pt, "white"), (loc, bg, pt)):
        if not txt:
            continue
        tw = d.textlength(txt, font=f)
        d.rounded_rectangle((cx, y0 + 70, cx + tw + 52, y0 + 136), 33, fill=fill)
        d.text((cx + 26, y0 + 103), txt, font=f, fill=col, anchor="lm")
        cx += tw + 52 + 16
    # 제목: 기관 / 부서 / 직무 단위 줄바꿈, 첫 줄 형광펜
    maxw = x1 - x0 - 140
    nmax = 4 if sq else 5
    for size in ((84, 74, 66, 58) if sq else (94, 84, 74, 66)):
        ft = font(size, "Title")
        lines: list[str] = []
        for sg in segs:
            lines += wrap(d, sg, ft, maxw, 3)
        if len(lines) <= nmax:
            break
    lines = lines[:nmax]
    lh = int(size * 1.3)
    y = y0 + (180 if sq else 200) + (nmax - len(lines)) * lh // 2 - 20
    for i, ln in enumerate(lines):
        if i == 0:
            tw = d.textlength(ln, font=ft)
            d.rounded_rectangle((x0 + 62, y + size * 0.55, x0 + 78 + tw, y + size * 1.05), 10, fill=mark)
        d.text((x0 + 70, y), ln, font=ft, fill="#1E1E1E")
        y += lh
    _sparkle(d, x1 - 95, y0 + 210, 26, mark)
    _sparkle(d, x1 - 140, y0 + 260, 14, mark)
    # 마감: 날짜 + D-day 스티커 (3일 이내면 '마감임박' 꼬리표)
    scx, scy, r = x1 - 150, y1 - 170, (100 if sq else 112)
    d.ellipse((scx - r + 8, scy - r + 10, scx + r + 8, scy + r + 10), fill=mark)
    d.ellipse((scx - r, scy - r, scx + r, scy + r), fill=pt)
    d.text((scx, scy - 4), dd, font=font(68 if len(dd) <= 4 else 56, "Title"), fill="white", anchor="mm")
    if left is not None and left <= 3:
        ft2 = font(30, "ExtraBold")
        tw = d.textlength("마감임박", font=ft2)
        d.rounded_rectangle((scx - tw / 2 - 20, scy - r - 30, scx + tw / 2 + 20, scy - r + 18), 24, fill="#1E1E1E")
        d.text((scx, scy - r - 6), "마감임박", font=ft2, fill="white", anchor="mm")
    label = "접수 마감" + (f" {job.deadline_time}까지" if job.deadline_time else "")
    d.text((x0 + 70, y1 - 225), label, font=font(36, "SemiBold"), fill="#8C8C8C")
    d.text((x0 + 70, y1 - 175), when, font=font(70, "ExtraBold"), fill="#1E1E1E")
    src = IG_SOURCE.get(job.source, "")
    d.text((W / 2, h - 65 if sq else H - 85), BRAND + (f"  ·  출처 {src}" if src else ""), font=font(30, "SemiBold"), fill=pt, anchor="mm")
    return img


def ig_posts(jobs: list[Job], today: date, out_dir: Path) -> list[list[Path]]:
    """블로그 글로 고른 공고마다 인스타 게시물 1개 (ig-01-1.jpg 표지, ig-01-2.jpg … 상세)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    posts = []
    for n, j in enumerate(jobs, start=1):
        paths = []
        for k, im in enumerate(ig_slides(j, today), start=1):
            pth = out_dir / f"ig-{n:02d}-{k}.jpg"
            im.save(pth, quality=93)
            paths.append(pth)
        posts.append(paths)
    return posts


# ---------- 인스타 상세 장 (표지 뒤에 넘겨보는 장) ----------
def _ig_frame(job: Job):
    bg, mark, pt, lab = IG_PAL.get(job.category or "기타", IG_PAL["기타"])
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    for i in range(0, W + 80, 120):
        for j in range(0, H + 80, 120):
            if (i // 120 + j // 120) % 2 == 0:
                d.ellipse((i - 7, j - 7, i + 7, j + 7), fill=mark)
    box = (80, 110, W - 80, H - 150)
    d.rounded_rectangle((box[0], box[1] + 12, box[2], box[3] + 12), 56, fill=mark)
    d.rounded_rectangle(box, 56, fill="white")
    return img, d, box, (bg, mark, pt)


def _ig_footer(d, job, pal, page: int, total: int) -> None:
    src = IG_SOURCE.get(job.source, "")
    d.text((W / 2, H - 85), BRAND + (f"  ·  출처 {src}" if src else ""), font=font(30, "SemiBold"), fill=pal[2], anchor="mm")
    d.text((W - 110, 160), f"{page}/{total}", font=font(30, "Bold"), fill="#B0B0B0", anchor="ra")


def _ig_heading(d, x, y, text, pal) -> int:
    ft = font(64, "Title")
    tw = d.textlength(text, font=ft)
    d.rounded_rectangle((x - 8, y + 36, x + tw + 8, y + 70), 10, fill=pal[1])
    d.text((x, y), text, font=ft, fill="#1E1E1E")
    return y + 120


def _ig_page(job: Job, sections: list[tuple[str, list[tuple[str, str]]]]):
    """한 장에 섹션 여러 개. 공간이 모자라면 남은 항목은 생략 (자세한 건 블로그)."""
    img, d, box, pal = _ig_frame(job)
    fv, fl = font(50, "SemiBold"), font(42, "Bold")
    x0, ylim = box[0] + 70, box[3] - 60
    maxw = box[2] - box[0] - 140
    y = box[1] + 110
    for si, (title, rows) in enumerate(sections):
        if si:
            y += 40
        if y + 150 > ylim:
            break
        y = _ig_heading(d, x0, y, title, pal)
        for label, val in rows:
            tx = x0 + (200 if label else 44)
            lines = wrap(d, val, fv, maxw - (tx - x0), 4)
            if y + len(lines) * 68 > ylim:
                break
            if label:
                d.text((x0, y + 6), label, font=fl, fill=pal[2])
            else:
                d.ellipse((x0 + 4, y + 24, x0 + 24, y + 44), fill=pal[1])
            for ln in lines:
                d.text((tx, y), ln, font=fv, fill="#2A2A2A"); y += 68
            y += 40
    return img, d, pal


def ig_slides(job: Job, today: date) -> list[Image.Image]:
    """인스타 4장: 표지 / 핵심 조건 / 핵심 자격 3개 / 한줄 TIP + 블로그 안내.
    판단에 필요한 정보만 인스타에, 우대·전형·복지·지원 링크는 블로그로."""
    from .blog import _org
    cond = [(k, v) for k, v in (
        ("급여", job.salary or ""), ("근무", job.work_hours or ""), ("계약", job.contract_period or ""),
        ("근무지", job.location or ""), ("인원", job.headcount or "")) if v]
    qual = [("", q) for q in (job.requirements or job.qualifications or [])[:3]]
    pages = []
    if cond:
        pages.append(_ig_page(job, [("핵심 조건", cond)]))
    if qual:
        img, d, pal = _ig_page(job, [("핵심 자격", qual)])
        more = [x for x, v in (("우대 사항", job.preferred), ("전형", job.process), ("복리후생", job.benefits)) if v]
        if more:
            box = (80, 110, W - 80, H - 150)
            cy = box[3] - 200
            d.rounded_rectangle((box[0] + 70, cy, box[2] - 70, cy + 120), 30, fill=pal[0])
            d.text((W / 2, cy + 60), " · ".join(more) + "은 블로그 참고", font=font(36, "SemiBold"), fill=pal[2], anchor="mm")
        pages.append((img, d, pal))
    # 마지막 장: 한줄 TIP + 블로그 찾는 법
    img, d, box, pal = _ig_frame(job)
    x0 = box[0] + 70
    y = _ig_heading(d, x0, box[1] + 110, "한줄 TIP", pal)
    tip = job.ig_tip or (job.summary or "").split(". ")[0]
    for ln in wrap(d, tip, font(50, "Bold"), box[2] - box[0] - 140, 6):
        d.text((x0, y), ln, font=font(50, "Bold"), fill="#1E1E1E"); y += 76
    key = _org(job).split()[-1] if _org(job) else ""
    cy = box[3] - 300
    d.rounded_rectangle((x0, cy, box[2] - 70, cy + 230), 36, fill=pal[0])
    d.text((W / 2, cy + 62), "지원 링크 · 전체 공고 정리는", font=font(40, "SemiBold"), fill="#555", anchor="mm")
    d.text((W / 2, cy + 128), "프로필 링크 → 블로그", font=font(54, "ExtraBold"), fill=pal[2], anchor="mm")
    if key:
        d.text((W / 2, cy + 188), f"블로그에서 '{key}' 검색", font=font(36, "SemiBold"), fill="#777", anchor="mm")
    _sparkle(d, box[2] - 95, box[1] + 150, 26, pal[1])
    pages.append((img, d, pal))
    total = len(pages) + 1
    out = [ig_post(job, today)]
    for n, (img, d, pal) in enumerate(pages, start=2):
        _ig_footer(d, job, pal, n, total)
        out.append(img)
    return out


def blog_thumb(job: Job, today: date) -> Image.Image:
    """블로그 목록용 정사각형 썸네일: 인스타 표지와 같은 색·형광펜, 목록 크기에서도 읽히게 제목을 크게."""
    from .blog import _emp, _org
    S = 1080
    bg, mark, pt, lab = IG_PAL.get(job.category or "기타", IG_PAL["기타"])
    role = job.job_role or ""
    emp = "" if "강사" in role else _emp(job)
    segs = [s for s in (_org(job), job.department or "", " ".join(f"{role} {emp if emp not in role else ''} 채용".split())) if s]
    dl = date.fromisoformat(job.deadline) if job.deadline else None
    img = Image.new("RGB", (S, S), bg)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 50, 50, S - 50, S - 50
    d.rounded_rectangle((x0, y0 + 10, x1, y1 + 10), 48, fill=mark)
    d.rounded_rectangle((x0, y0, x1, y1), 48, fill="white")
    X = x0 + 70
    for size in (120, 108, 96, 86, 78):
        ft = font(size, "Title")
        lines: list[str] = []
        for sg in segs:
            lines += wrap(d, sg, ft, x1 - X - 60, 3)
        if len(lines) <= 4:
            break
    lines = lines[:4]
    lh = int(size * 1.25)
    y = y0 + 90
    for i, ln in enumerate(lines):
        if i == 0:
            tw = d.textlength(ln, font=ft)
            d.rounded_rectangle((X - 8, y + size * 0.55, X + tw + 8, y + size * 1.05), 12, fill=mark)
        d.text((X, y), ln, font=ft, fill="#1E1E1E")
        y += lh
    _sparkle(d, x1 - 80, y0 + 90, 34, mark)
    # 하단: 마감일(크게) + 지역
    when = f"~{dl.month}/{dl.day}({WEEK[dl.weekday()]})" if dl else "상시 채용"
    loc = (job.location or "").split(",")[0].replace("특별시", "").replace("광역시", "").strip()
    fb = font(76, "ExtraBold")
    tw = d.textlength(when, font=fb)
    by = y1 - 190
    d.rounded_rectangle((X - 10, by, X + tw + 50, by + 120), 60, fill=pt)
    d.text((X + 20, by + 60), when + " 마감", font=fb, fill="white", anchor="lm") if False else d.text((X + 20, by + 60), when, font=fb, fill="white", anchor="lm")
    if loc:
        d.text((x1 - 70, by + 60), loc, font=font(58, "Bold"), fill=pt, anchor="rm")
    return img

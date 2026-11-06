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

BRAND = os.environ.get("BRAND_NAME") or "병원 밖 간호사"
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

"""인스타그램 카드뉴스 이미지 생성 (1080x1350, 4:5 비율).

카드 구성: 표지 1장 + 공고 카드 최대 8장 + 마무리 1장 (인스타 캐러셀 최대 10장)
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

# 색상: 흰 바탕 + 검정 글자 + 포인트 색 하나 (카테고리 색은 작은 라벨에만)
BG = "#FAFAF7"
INK = "#111111"
SUB = "#555555"
MUTED = "#9A9A9A"
LINE = "#E4E4E0"
ACCENT = "#0B6E4F"
ACCENT_SOFT = "#E7F1EC"
WHITE = "#FFFFFF"

PALETTE = {"공공": "#2F5FD0", "학교": "#0B8457", "기업": "#D9480F", "연구": "#6741D9"}

_cache: dict = {}


def font(size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    k = (size, weight)
    if k not in _cache:
        path = FONT_DIR / f"Pretendard-{weight}.otf"
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

def _header(d: ImageDraw.ImageDraw, idx: int, total: int, color=MUTED):
    d.text((PAD, 76), BRAND, font=font(26, "SemiBold"), fill=color, anchor="lm")
    d.text((W - PAD, 76), f"{idx:02d} / {total:02d}", font=font(26, "Medium"), fill=color, anchor="rm")


def _rule(d: ImageDraw.ImageDraw, y: int, color=LINE, width=2):
    d.line([(PAD, y), (W - PAD, y)], fill=color, width=width)


def _short_loc(loc: str | None) -> str:
    if not loc:
        return "공고 참고"
    parts = [x.strip() for x in loc.replace(">", " ").split(",") if x.strip()]
    if not parts:
        return "공고 참고"
    return parts[0][:10] + (f" 외 {len(parts) - 1}곳" if len(parts) > 1 else "")


# ---------- 카드 ----------

def cover(jobs: list[Job], today: date, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _header(d, 1, total)
    _rule(d, 120, INK, 3)

    d.text((PAD, 168), f"{today.year}. {today.month:02d}. {today.day:02d}", font=font(30, "SemiBold"), fill=ACCENT)
    d.text((PAD, 236), "오늘의", font=font(108, "ExtraBold"), fill=INK)
    d.text((PAD, 362), "탈임상 공고", font=font(108, "ExtraBold"), fill=INK)

    num = str(len(jobs))
    nf = font(260, "ExtraBold")
    d.text((PAD - 8, 500), num, font=nf, fill=ACCENT)
    nw = d.textlength(num, font=nf)
    d.text((PAD + nw + 8, 740), "건", font=font(80, "Bold"), fill=ACCENT, anchor="ls")

    y = 830
    _rule(d, y)
    for cat, meta in CATEGORIES.items():
        n = sum(1 for j in jobs if j.category == cat)
        if not n:
            continue
        d.rectangle([PAD, y + 44, PAD + 14, y + 58], fill=PALETTE.get(cat, SUB))
        d.text((PAD + 34, y + 51), cat, font=font(38, "Bold"), fill=INK, anchor="lm")
        d.text((PAD + 140, y + 51), meta["desc"], font=font(28, "Regular"), fill=MUTED, anchor="lm")
        d.text((W - PAD, y + 51), f"{n}", font=font(40, "Bold"), fill=INK, anchor="rm")
        y += 102
        _rule(d, y)

    d.text((PAD, H - 92), "넘겨서 확인하기", font=font(32, "SemiBold"), fill=INK, anchor="lm")
    d.text((W - PAD, H - 92), "→", font=font(40, "SemiBold"), fill=INK, anchor="rm")
    return img


def job_card(job: Job, today: date, idx: int, total: int) -> Image.Image:
    cat_col = PALETTE.get(job.category or "", SUB)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _header(d, idx, total)
    _rule(d, 120, INK, 3)

    # 카테고리 라벨
    y = 170
    d.rectangle([PAD, y + 8, PAD + 14, y + 22], fill=cat_col)
    d.text((PAD + 30, y + 15), f"{job.category or '기타'}  ·  {job.org.replace('(주)', '').strip()}"[:34],
           font=font(30, "SemiBold"), fill=SUB, anchor="lm")

    # 직무명
    y += 70
    role_f = font(92, "ExtraBold")
    role_lines = wrap(d, job.job_role or job.title, role_f, W - PAD * 2, 2)
    for line in role_lines:
        d.text((PAD, y), line, font=role_f, fill=INK)
        y += 112

    # 공고명 (작게) - 직무명이 두 줄이면 한 줄만
    for line in wrap(d, job.title, font(28, "Regular"), W - PAD * 2, 3 - len(role_lines)):
        d.text((PAD, y + 4), line, font=font(28, "Regular"), fill=MUTED)
        y += 42

    # 마감
    y += 44
    label, dl = d_label(job.deadline, today)
    urgent = label == "D-DAY" or (label.startswith("D-") and label[2:].isdigit() and int(label[2:]) <= 3)
    lf = font(64, "ExtraBold")
    d.text((PAD, y), label, font=lf, fill="#D63031" if urgent else ACCENT)
    lw = d.textlength(label, font=lf)
    if dl:
        d.text((PAD + lw + 24, y + 44), f"{dl.month}월 {dl.day}일 마감", font=font(32, "Medium"), fill=SUB, anchor="ls")
    y += 104

    # 정보 표
    _rule(d, y)
    for k, v in (("근무지", _short_loc(job.location)), ("고용형태", (job.employment_type or "공고 참고").split(",")[0])):
        d.text((PAD, y + 40), k, font=font(30, "Medium"), fill=MUTED, anchor="lm")
        d.text((PAD + 200, y + 40), v, font=font(32, "SemiBold"), fill=INK, anchor="lm")
        y += 80
        _rule(d, y)

    # 요약
    y += 40
    reqs = job.requirements[:3]
    bottom = H - 150  # 하단 구분선 위 여백
    req_h = (56 + 52 * len(reqs) + 30) if reqs else 0
    sum_f = font(34, "Regular")
    max_lines = max(2, min(4, (bottom - y - req_h) // 54))
    if reqs and y + max_lines * 54 + req_h > bottom:  # 공간이 모자라면 자격요건 개수를 줄임
        while reqs and y + 2 * 54 + (56 + 52 * len(reqs) + 30) > bottom:
            reqs = reqs[:-1]
        req_h = (56 + 52 * len(reqs) + 30) if reqs else 0
        max_lines = max(2, min(4, (bottom - y - req_h) // 54))
    for line in wrap(d, job.summary or "", sum_f, W - PAD * 2, max_lines):
        d.text((PAD, y), line, font=sum_f, fill=INK)
        y += 54

    # 지원 자격
    if reqs:
        y += 30
        d.text((PAD, y), "지원 자격", font=font(28, "Bold"), fill=ACCENT)
        y += 52
        for r in reqs:
            if y + 44 > bottom:
                break
            d.text((PAD, y), "—", font=font(30, "Medium"), fill=MUTED)
            d.text((PAD + 48, y), wrap(d, r, font(31, "Medium"), W - PAD * 2 - 48, 1)[0], font=font(31, "Medium"), fill=SUB)
            y += 52

    _rule(d, H - 130)
    d.text((PAD, H - 82), "원문 링크는 프로필에서", font=font(26, "Medium"), fill=MUTED, anchor="lm")
    if HANDLE:
        d.text((W - PAD, H - 82), f"@{HANDLE}", font=font(26, "SemiBold"), fill=MUTED, anchor="rm")
    return img


def outro(total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), ACCENT)
    d = ImageDraw.Draw(img)
    soft = "#9CC7B5"
    _header(d, total, total, soft)
    d.line([(PAD, 120), (W - PAD, 120)], fill=WHITE, width=3)
    d.text((PAD, 420), "저장해두고", font=font(104, "ExtraBold"), fill=WHITE)
    d.text((PAD, 546), "마감 놓치지 마세요", font=font(104, "ExtraBold"), fill=WHITE)
    d.text((PAD, 720), "병원 밖 간호사 채용 공고를", font=font(36, "Medium"), fill=soft)
    d.text((PAD, 772), "매일 아침 정리해서 올려요.", font=font(36, "Medium"), fill=soft)
    d.line([(PAD, H - 200), (W - PAD, H - 200)], fill=soft, width=2)
    d.text((PAD, H - 140), "전체 공고 · 원문 링크", font=font(32, "Medium"), fill=soft, anchor="lm")
    d.text((W - PAD, H - 140), "프로필 링크", font=font(32, "Bold"), fill=WHITE, anchor="rm")
    d.text((PAD, H - 80), "팔로우하고 받아보기", font=font(32, "Medium"), fill=soft, anchor="lm")
    d.text((W - PAD, H - 80), f"@{HANDLE}" if HANDLE else BRAND, font=font(32, "Bold"), fill=WHITE, anchor="rm")
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
    images.append(outro(total))
    paths = []
    for i, im in enumerate(images):
        p = out_dir / f"card-{i:02d}.jpg"
        im.save(p, quality=93)
        paths.append(p)
    return paths

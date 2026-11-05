"""인스타그램 카드뉴스 이미지 생성 (1080x1350, 4:5 비율).

카드 구성: 표지 1장 + 공고 카드 최대 9장 (인스타 캐러셀 최대 10장)
"""
from __future__ import annotations

import glob
import os
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import CATEGORIES, Job

W, H = 1080, 1350
BG = "#F8FAFC"
INK = "#0F172A"
MUTED = "#64748B"
BRAND = os.environ.get("BRAND_NAME", "병원 밖 간호사")
HANDLE = os.environ.get("IG_HANDLE", "")


def _font_path(bold: bool) -> str:
    env = os.environ.get("FONT_BOLD" if bold else "FONT_REGULAR")
    if env:
        return env
    name = "Bold" if bold else "Regular"
    hits = glob.glob(f"/usr/share/fonts/**/NotoSansCJK-{name}.ttc", recursive=True)
    if not hits:
        raise RuntimeError("한글 폰트가 없습니다: sudo apt-get install fonts-noto-cjk")
    return hits[0]


_cache: dict = {}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    k = (size, bold)
    if k not in _cache:
        # .ttc 안에서 index 1 = 한국어(KR) 글꼴
        _cache[k] = ImageFont.truetype(_font_path(bold), size, index=1)
    return _cache[k]


def wrap(draw: ImageDraw.ImageDraw, text: str, f, max_w: int, max_lines: int) -> list[str]:
    """한글은 글자 단위, 공백 기준 우선으로 줄바꿈."""
    lines, cur = [], ""
    for ch in text.replace("\n", " "):
        trial = cur + ch
        if draw.textlength(trial, font=f) <= max_w:
            cur = trial
            continue
        # 공백에서 끊을 수 있으면 단어 단위로
        if " " in cur and ch != " ":
            head, tail = cur.rsplit(" ", 1)
            lines.append(head)
            cur = tail + ch
        else:
            lines.append(cur)
            cur = ch.lstrip()
        if len(lines) == max_lines:
            break
    if len(lines) < max_lines and cur.strip():
        lines.append(cur)
    if len(lines) == max_lines and "".join(lines) != text.replace("\n", " ").strip():
        last = lines[-1]
        while last and draw.textlength(last + "…", font=f) > max_w:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def d_day(deadline: str | None, today: date) -> str:
    if not deadline:
        return "상시/채용시 마감"
    try:
        dl = date.fromisoformat(deadline)
    except ValueError:
        return deadline
    n = (dl - today).days
    label = "D-DAY" if n == 0 else (f"D-{n}" if n > 0 else "마감")
    return f"{label} · {dl.month}/{dl.day} 마감"


def _chip(draw, x, y, text, color, size=34) -> int:
    f = font(size, True)
    tw = draw.textlength(text, font=f)
    pad_x, h = 26, size + 28
    draw.rounded_rectangle([x, y, x + tw + pad_x * 2, y + h], radius=h // 2, fill=color)
    draw.text((x + pad_x, y + h / 2), text, font=f, fill="white", anchor="lm")
    return int(x + tw + pad_x * 2)


def _footer(draw, idx: int, total: int):
    draw.line([80, H - 130, W - 80, H - 130], fill="#E2E8F0", width=2)
    left = f"{BRAND}" + (f"  @{HANDLE}" if HANDLE else "")
    draw.text((80, H - 75), left, font=font(30, True), fill=MUTED, anchor="lm")
    draw.text((W - 80, H - 75), f"{idx}/{total}", font=font(30), fill=MUTED, anchor="rm")


def cover(jobs: list[Job], today: date, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    d.text((80, 150), f"{today.year}.{today.month:02d}.{today.day:02d}", font=font(40), fill="#94A3B8")
    d.text((80, 230), "오늘의", font=font(96, True), fill="white")
    d.text((80, 345), "탈임상 공고", font=font(96, True), fill="white")
    d.text((80, 470), f"{len(jobs)}건", font=font(150, True), fill="#38BDF8")

    y = 720
    for cat, meta in CATEGORIES.items():
        n = sum(1 for j in jobs if j.category == cat)
        if not n:
            continue
        _chip(d, 80, y, cat, meta["color"], 40)
        d.text((260, y + 34), f"{n}건  ·  {meta['desc']}", font=font(36), fill="#CBD5E1", anchor="lm")
        y += 105
    d.text((80, H - 200), "옆으로 넘겨서 확인하세요  →", font=font(38, True), fill="white")
    d.text((80, H - 75), BRAND + (f"  @{HANDLE}" if HANDLE else ""), font=font(30, True), fill="#94A3B8", anchor="lm")
    d.text((W - 80, H - 75), f"1/{total}", font=font(30), fill="#94A3B8", anchor="rm")
    return img


def job_card(job: Job, today: date, idx: int, total: int) -> Image.Image:
    meta = CATEGORIES.get(job.category or "", {"color": "#475569"})
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 16], fill=meta["color"])

    x_end = _chip(d, 80, 90, job.category or "기타", meta["color"])
    if job.job_role and job.job_role != job.category:
        _chip(d, x_end + 16, 90, job.job_role[:14], "#334155")

    y = 220
    d.text((80, y), job.org[:24], font=font(44, True), fill=meta["color"])
    y += 80
    for line in wrap(d, job.title, font(56, True), W - 160, 3):
        d.text((80, y), line, font=font(56, True), fill=INK)
        y += 76

    y += 20
    d.rounded_rectangle([80, y, W - 80, y + 90], radius=20, fill="white", outline="#E2E8F0", width=2)
    info = d_day(job.deadline, today)
    if job.location:
        info += f"  ·  {job.location.split(',')[0][:12]}"
    d.text((110, y + 45), info, font=font(36, True), fill=INK, anchor="lm")
    y += 130

    for line in wrap(d, job.summary or "", font(38), W - 160, 5):
        d.text((80, y), line, font=font(38), fill="#334155")
        y += 58

    if job.requirements:
        y += 30
        d.text((80, y), "자격요건", font=font(36, True), fill=INK)
        y += 60
        for req in job.requirements[:3]:
            for i, line in enumerate(wrap(d, req, font(34), W - 200, 2)):
                if y > H - 200:
                    break
                d.text((80 if i == 0 else 118, y), ("•  " if i == 0 else "") + line, font=font(34), fill="#334155")
                y += 50

    _footer(d, idx, total)
    return img


def render_all(jobs: list[Job], today: date, out_dir: Path, limit: int = 9) -> list[Path]:
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
    total = len(picked) + 1
    paths = []
    p = out_dir / "card-00.jpg"
    cover(jobs, today, total).save(p, quality=92)
    paths.append(p)
    for i, j in enumerate(picked, start=2):
        p = out_dir / f"card-{i - 1:02d}.jpg"
        job_card(j, today, i, total).save(p, quality=92)
        paths.append(p)
    return paths

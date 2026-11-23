"""주 1회 '탈임상 가이드' 글 (취업 꿀팁·자격증·자소서/면접).

  data/guides/YYYY-MM-DD.json  →  docs/guides/YYYY-MM-DD/
    - 네이버 블로그 본문 (복사 버튼) + 썸네일
    - 인스타 카드뉴스 (표지 + 섹션별 1장 + 마무리) + 캡션

주제 대기열: data/guides/topics.md  (- [ ] 주제  형식, 위에서부터 사용)
"""
from __future__ import annotations

import html
import json
import os
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from .render import BRAND, H, W, font, wrap

AUTHOR = "리브"
# 네이버 블로그에 만든 카테고리 이름과 같아야 함
GUIDE_CATEGORIES = {
    "자소서/면접": "탈임상 가이드 > 자소서/면접",
    "병원 밖 업무 스킬": "탈임상 가이드 > 병원 밖 업무 스킬",
    "공고 분석": "탈임상 가이드 > 공고 분석",   # 수요일 수집 공고 정리 글
}
BASE_TAGS = ["탈임상", "탈임상간호사", "간호사이직", "간호사취업"]


def _e(s) -> str:
    return html.escape(str(s or "")).strip()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check(g: dict) -> list[str]:
    errs = []
    for k in ("title", "category", "cover", "intro", "sections", "comment"):
        if not g.get(k):
            errs.append(f"'{k}' 비어있음")
    if g.get("category") and g["category"] not in GUIDE_CATEGORIES:
        errs.append(f"category 는 {list(GUIDE_CATEGORIES)} 중 하나")
    if not 1 <= len(g.get("cover") or []) <= 3:
        errs.append("cover 는 1~3줄")
    for line in g.get("cover") or []:
        if len(line) > 10:
            errs.append(f"cover 한 줄은 10자 이내: '{line}'")
    secs = g.get("sections") or []
    if not 3 <= len(secs) <= 7:
        errs.append("sections 는 3~7개 (카드뉴스 최대 10장)")
    for i, s in enumerate(secs, 1):
        if not s.get("heading"):
            errs.append(f"섹션 {i}: heading 비어있음")
        if not (s.get("paragraphs") or s.get("bullets")):
            errs.append(f"섹션 {i}: paragraphs/bullets 둘 다 비어있음")
        card = s.get("card") or []
        if not 1 <= len(card) <= 4:
            errs.append(f"섹션 {i}: card 는 1~4줄")
        for c in card:
            if len(c) > 42:
                errs.append(f"섹션 {i}: card 한 줄은 42자 이내: '{c[:20]}…'")
        if len(s.get("card_title") or s.get("heading") or "") > 16:
            errs.append(f"섹션 {i}: card_title(없으면 heading)은 16자 이내")
    return errs


def tags(g: dict) -> list[str]:
    out = []
    for t in list(g.get("tags") or []) + BASE_TAGS:
        t = t.replace(" ", "").lstrip("#")
        if t and t not in out:
            out.append(t)
    return out[:10]


# ---------- 블로그 ----------

ASK = "이 밖에 더 궁금한 점이나\n다뤄줬으면 하는 주제가 있다면\n댓글로 남겨주세요.\n다음 글에서 다뤄보겠습니다."
PAGES = (os.environ.get("PAGES_BASE_URL") or "https://a55796196-sudo.github.io/nurse_jobs").rstrip("/")
C = 'style="text-align:center"'


def _br(text: str) -> str:
    """줄바꿈(\n)을 살린 가운데 정렬 문단. 한 줄에 한 문장씩 짧게."""
    return f"<p {C}>" + "<br>".join(_e(x) for x in str(text).split("\n")) + "</p>"


def _gap() -> str:
    return f"<p {C}>&nbsp;</p>"


def post_html(g: dict, day: str = "") -> str:
    """네이버 블로그용 본문. 가운데 정렬 · 짧은 줄 · 인용구 소제목 · 구분선 · 카드 이미지 사이사이."""
    img = (lambda n: f'<p {C}><img src="{PAGES}/guides/{day}/card-{n:02d}.jpg" width="540" alt="카드 {n}"></p>') if day else (lambda n: "")
    out = [img(0), _gap(), _br(g["intro"]), _gap(), "<hr>"]
    for n, s in enumerate(g["sections"], 1):
        out.append(f'<blockquote {C}><p {C}><b>{_e(s["heading"])}</b></p></blockquote>')
        out.append(img(n))
        for p in s.get("paragraphs") or []:
            out += [_br(p), _gap()]
        if s.get("bullets"):
            out += [f"<p {C}>" + "<br>".join("✔️ " + _e(b) for b in s["bullets"]) + "</p>", _gap()]
        if s.get("tip"):
            out += [f"<p {C}>(💡 {_e(s['tip'])})</p>", _gap()]
        out.append("<hr>")
    out += [_br(g["comment"]), _gap()]
    if g.get("links"):
        out.append(f"<p {C}><b>공식 정보 확인</b><br>" + "<br>".join(
            f'<a href="{_e(l["url"])}">{_e(l["name"])}</a>' + (f" · {_e(l['desc'])}" if l.get("desc") else "") for l in g["links"]) + "</p>")
        out.append(f"<p {C}>※ 시험 일정·응시 자격·비용은 바뀔 수 있으니 준비 전 공식 사이트에서 확인하시기 바랍니다.</p>")
    out.append("<hr>")
    out += [_br(ASK), _gap()]
    from .blog import ig_cta_html
    out += [ig_cta_html(center=True), _br("읽어주셔서 감사합니다."), _gap()]
    out.append(f"<p {C}>" + " ".join(f"#{_e(t)}" for t in tags(g)) + "</p>")
    return "\n".join(x for x in out if x)


def caption(g: dict) -> str:
    lines = [f"💡 {g.get('caption_hook') or g['title']}", ""]
    for i, s in enumerate(g["sections"], 1):
        lines.append(f"{i}. {s.get('card_title') or s['heading']}")
    lines += ["", "💬 더 궁금한 점이나 다뤄줬으면 하는 주제가 있다면 댓글로 알려주세요"]
    lines += ["", "📌 자세한 내용은 프로필 링크(블로그)에서 확인하세요!", "💾 저장해두고 필요할 때 꺼내보세요", ""]
    lines.append(" ".join("#" + t for t in tags(g) + ["간호사", "간호사채용"]))
    return "\n".join(lines)


# ---------- 이미지 (연노랑 포스터 표지 · 줄노트 · 포스트잇) ----------
# 공고 카드(색 도트 배경 + 흰 카드)와 구분되도록 틀 없이, 블로그 바탕과 같은 연노랑.
G_BG, G_MARK, G_PT = "#FFFCF3", "#FFE24D", "#B07A12"
G_PAPER, G_RULE, G_SHADOW, G_SUB = "#FFFFFF", "#F1EBDA", "#ECE5D2", "#5A5345"
G_INK = "#1E1E1E"


def _t(s: str) -> str:
    """제목 글꼴(Black Han Sans)에 없는 가운뎃점은 / 로."""
    return s.replace("·", "/")


def _sparkle(d, x, y, r, col):
    from .render import _sparkle as sp
    sp(d, x, y, r, col)


def _hl(d, x, y, text, ft, size):
    tw = d.textlength(text, font=ft)
    d.rounded_rectangle((x - 8, y + size * 0.55, x + tw + 8, y + size * 1.05), 12, fill=G_MARK)
    d.text((x, y), text, font=ft, fill=G_INK)


def _foot(d, page=None, total=None, h=H):
    d.text((80, h - 80), BRAND, font=font(30, "SemiBold"), fill=G_PT, anchor="lm")
    if page:
        d.text((W - 80, h - 80), f"{page} / {total}", font=font(30, "Bold"), fill=G_PT, anchor="rm")


def _label(g: dict) -> str:
    return f"{g['series']} {int(g.get('series_no') or 1):02d}" if g.get("series") else g["category"]


def _cover(g: dict, total: int, h: int = H) -> Image.Image:
    img = Image.new("RGB", (W, h), G_BG)
    d = ImageDraw.Draw(img)
    X = 90
    d.text((X, 130), "리브의 탈임상 노트", font=font(40, "ExtraBold"), fill=G_PT)
    d.text((X, 186), _label(g), font=font(40, "SemiBold"), fill=G_PT)
    d.line((X, 260, W - 90, 260), fill=G_PT, width=4)
    lines = [_t(x) for x in g["cover"]]
    for size in ((150, 136, 120, 108) if h == H else (132, 120, 108, 96)):
        ft = font(size, "Title")
        if all(d.textlength(x, font=ft) <= W - 2 * X for x in lines):
            break
    y = 340 if h == H else 310
    for i, ln in enumerate(lines):
        if i == len(lines) - 1:
            _hl(d, X, y, ln, ft, size)
        else:
            d.text((X, y), ln, font=ft, fill=G_INK)
        y += int(size * 1.22)
    if h == H and g.get("subtitle"):
        for ln in wrap(d, g["subtitle"], font(50, "Bold"), W - 2 * X, 2):
            d.text((X, y + 20), ln, font=font(50, "Bold"), fill=G_SUB)
            y += 70
    _sparkle(d, W - 130, 165, 40, G_MARK)
    _sparkle(d, W - 195, 215, 18, G_MARK)
    if h == H:
        d.text((X, H - 190), "넘겨서 보기 →", font=font(56, "ExtraBold"), fill=G_INK, anchor="lm")
        _foot(d)
    return img


def _paper(img: Image.Image, box) -> ImageDraw.ImageDraw:
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    d.rectangle((x0 + 10, y0 + 14, x1 + 10, y1 + 14), fill=G_SHADOW)
    d.rectangle(box, fill=G_PAPER)
    tape = Image.new("RGBA", (220, 64), (255, 226, 77, 120)).rotate(-4, expand=True)
    img.paste(tape, (int((x0 + x1) / 2 - 115), y0 - 34), tape)
    return d


def _section(g: dict, s: dict, n: int, idx: int, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), G_BG)
    box = (80, 130, W - 80, H - 150)
    d = _paper(img, box)
    x0, y0, x1, y1 = box
    X = x0 + 70
    d.text((X, y0 + 80), f"POINT {n:02d}", font=font(34, "ExtraBold"), fill=G_PT)
    ft = font(76, "Title")
    y = y0 + 135
    for ln in wrap(d, _t(s.get("card_title") or s["heading"]), ft, x1 - X - 60, 2):
        _hl(d, X, y, ln, ft, 76)
        y += 100
    top = y + 60
    for size, LH in ((48, 92), (44, 84), (40, 76)):  # 줄노트 칸에 다 들어가는 크기
        fv = font(size, "SemiBold")
        rows: list[tuple[str, str]] = []
        for i, p in enumerate(s.get("card") or [], 1):
            ws = wrap(d, p, fv, x1 - X - 140, 3)
            rows += [(f"{i:02d}", ws[0])] + [("", w) for w in ws[1:]] + [("", "")]
        rows = rows[:-1]
        if top + len(rows) * LH <= y1 - 40:
            break
    yy = top
    while yy + LH - 18 < y1 - 30:
        d.line((x0 + 40, yy + LH - 18, x1 - 40, yy + LH - 18), fill=G_RULE, width=3)
        yy += LH
    for i, (num, txt) in enumerate(rows):
        ry = top + i * LH + 14
        if num:
            d.text((X, ry), num, font=font(size, "Title"), fill=G_PT)
        d.text((X + 100, ry), txt, font=fv, fill="#2A2A2A")
    _foot(d, idx, total)
    return img


def _closing(g: dict, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), G_BG)
    d = ImageDraw.Draw(img)
    S = 760
    note = Image.new("RGBA", (S + 40, S + 40), (0, 0, 0, 0))
    nd = ImageDraw.Draw(note)
    nd.rectangle((24, 30, S + 24, S + 30), fill=G_SHADOW)
    nd.rectangle((10, 10, S + 10, S + 10), fill="#FFF6B8")
    nd.text((70, 80), "리브의 한 줄", font=font(60, "Title"), fill=G_PT)
    yy = 200
    for ln in wrap(nd, g.get("closing") or g["comment"], font(50, "Bold"), S - 120, 8):
        nd.text((70, yy), ln, font=font(50, "Bold"), fill=G_INK)
        yy += 74
    note = note.rotate(3, expand=True, resample=Image.BICUBIC)
    img.paste(note, ((W - note.width) // 2, 140), note)
    if g.get("next_title"):
        d.text((90, H - 330), "다음 편", font=font(36, "ExtraBold"), fill=G_PT)
        d.text((90, H - 270), wrap(d, g["next_title"], font(50, "Bold"), W - 180, 1)[0], font=font(50, "Bold"), fill=G_INK)
    d.text((90, H - 190), "저장해두고 프로필 링크에서 전문 보기", font=font(40, "SemiBold"), fill=G_SUB)
    _sparkle(d, W - 140, 150, 36, G_MARK)
    _foot(d, total, total)
    return img


def thumb(g: dict) -> Image.Image:
    """블로그 썸네일: 표지와 같은 포스터형 정사각형. 블로그 바탕(연노랑)에서 경계가 보이게 옅은 베이지 테두리."""
    img = _cover(g, 0, h=1080)
    ImageDraw.Draw(img).rectangle((0, 0, W - 1, 1079), outline="#E6DCC2", width=14)
    return img


def render(g: dict, out: Path) -> list[Path]:
    secs = g["sections"]
    total = len(secs) + 2
    imgs = [_cover(g, total)] + [_section(g, s, n, n + 1, total) for n, s in enumerate(secs, 1)] + [_closing(g, total)]
    paths = []
    for i, im in enumerate(imgs):
        p = out / f"card-{i:02d}.jpg"
        im.save(p, quality=93)
        paths.append(p)
    return paths


# ---------- 작업실 페이지 ----------

def build(path: Path, docs: Path) -> Path:
    from .site import SCRIPT, STYLE
    g = load(path)
    errs = check(g)
    if errs:
        raise SystemExit("가이드 글 필드를 확인하세요:\n" + "\n".join(errs))
    day = path.stem
    out = docs / "guides" / day
    out.mkdir(parents=True, exist_ok=True)
    cards = render(g, out)
    thumb(g).save(out / "thumb.png")
    imgs = "".join(f'<a href="{p.name}" download><img src="{p.name}" alt="카드 {i}"></a>' for i, p in enumerate(cards))
    tg = " ".join("#" + t for t in tags(g))
    cap = caption(g)
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{_e(day)} 탈임상 가이드</title>
<style>{STYLE}</style></head><body><main>
<p class="muted"><a href="../../">← 작업실 첫 화면</a></p>
<h1>💡 {_e(day)} 탈임상 가이드</h1>

<div class="box"><div class="row"><b>블로그 글</b><span class="muted">카테고리: {_e(GUIDE_CATEGORIES[g['category']])}</span></div>
<div class="row" style="margin-top:8px"><pre id="pt" style="flex:1;margin:0">{_e(g['title'])}</pre>
<button onclick="copyText('pt',this)">제목 복사</button></div>
<details open><summary class="muted" style="margin:10px 0;cursor:pointer">본문 미리보기 (접기)</summary>
<div id="pb" class="post">{post_html(g, day)}</div></details>
<div class="row"><span class="muted">제목 → 본문 순서로 붙여넣기. 카드 이미지가 같이 안 붙으면 아래 카드뉴스를 저장해 그 자리에 넣고, 글꼴은 나눔마루부리로 바꾸세요</span>
<button onclick="copyHtml('pb',this)">본문 복사</button></div>
<div class="row" style="margin-top:10px"><pre id="tg" style="flex:1;margin:0">{_e(tg)}</pre>
<button onclick="copyText('tg',this)">태그 복사</button></div>
<div class="row" style="margin-top:10px;align-items:flex-start"><a href="thumb.png" download><img src="thumb.png" alt="썸네일" style="width:160px;border-radius:8px;border:1px solid var(--line)"></a>
<span class="muted">썸네일: 이미지를 눌러 저장 후 글 맨 위에 넣으세요</span></div></div>

<div class="box"><div class="row"><b>📷 인스타 카드뉴스</b><span class="muted">이미지를 눌러 저장</span></div>
<div class="cards">{imgs}</div></div>

<div class="box"><div class="row"><b>📷 인스타 캡션</b><button onclick="copyText('cap',this)">캡션 복사</button></div>
<pre id="cap">{_e(cap)}</pre></div>
</main><script>{SCRIPT}</script></body></html>"""
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "caption.txt").write_text(cap, encoding="utf-8")
    (out / "guide.json").write_text(json.dumps({"title": g["title"], "category": g["category"]}, ensure_ascii=False), encoding="utf-8")
    return out


def index_items(docs: Path) -> list[str]:
    """작업실 첫 화면 목록: 올릴 예정인 글(오늘 이후)은 날짜 순으로 전부, 지난 글은 최근 20개."""
    gdir = docs / "guides"
    if not gdir.exists():
        return []
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    dirs = sorted(p for p in gdir.iterdir() if p.is_dir())
    upcoming = [d for d in dirs if d.name >= today]
    past = [d for d in dirs if d.name < today][::-1][:20]

    def li(d):
        try:
            meta = json.loads((d / "guide.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {"title": "", "category": ""}
        wd = "월화수목금토일"[date.fromisoformat(d.name).weekday()]
        return f'<li><a href="guides/{d.name}/">{d.name} ({wd})</a> <span class="muted">· {_e(meta["category"])}</span><br>{_e(meta["title"])}</li>'

    items = []
    if upcoming:
        items.append(f'<li class="muted" style="list-style:none;margin-left:-1.2em"><b>올릴 예정 ({len(upcoming)}편, 날짜 순)</b></li>')
        items += [li(d) for d in upcoming]
    if past:
        items.append('<li class="muted" style="list-style:none;margin:12px 0 0 -1.2em"><b>지난 글</b></li>')
        items += [li(d) for d in past]
    return items

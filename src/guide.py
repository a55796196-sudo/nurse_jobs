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

from .render import BG, BRAND, H, HANDLE, INK, LINE, MUTED, PAD, SUB, W, _header, _marked, font, wrap

AUTHOR = "리브"
# 네이버 블로그에 만든 카테고리 이름과 같아야 함
GUIDE_CATEGORIES = {
    "자소서/면접": "탈임상 가이드 > 자소서/면접",
    "병원 밖 업무 스킬": "탈임상 가이드 > 병원 밖 업무 스킬",
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
    out += ["<hr>", _br((g.get("next_teaser") + "\n" if g.get("next_teaser") else "") + "읽어주셔서 감사합니다."), _gap()]
    out.append(f"<p {C}>" + " ".join(f"#{_e(t)}" for t in tags(g)) + "</p>")
    return "\n".join(x for x in out if x)


def caption(g: dict) -> str:
    lines = [f"💡 {g.get('caption_hook') or g['title']}", ""]
    for i, s in enumerate(g["sections"], 1):
        lines.append(f"{i}. {s.get('card_title') or s['heading']}")
    lines += ["", "📌 자세한 내용은 프로필 링크(블로그)에서 확인하세요!", "💾 저장해두고 필요할 때 꺼내보세요", ""]
    lines.append(" ".join("#" + t for t in tags(g) + ["간호사", "간호사채용"]))
    return "\n".join(lines)


# ---------- 이미지 ----------

def _t(s: str) -> str:
    """제목 글꼴(Black Han Sans)에 없는 가운뎃점은 / 로."""
    return s.replace("·", "/")


def _cover(g: dict, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _header(d, BRAND, "탈임상 가이드")
    lines = [_t(x) for x in g["cover"]]
    size = 150 if max(len(x) for x in lines) <= 6 else 120
    t = font(size, "Title")
    y = 300
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            _marked(d, PAD, y, line, t)
        else:
            d.text((PAD, y), line, font=t, fill=INK)
        y += int(size * 1.3)
    y += 40
    for line in wrap(d, g.get("subtitle") or "", font(42, "Medium"), W - PAD * 2, 3):
        d.text((PAD, y), line, font=font(42, "Medium"), fill=SUB)
        y += 62
    d.text((PAD, H - 100), "넘겨서 확인하기 →", font=font(36, "Bold"), fill=INK, anchor="lm")
    d.text((W - PAD, H - 100), f"1 / {total}", font=font(30, "SemiBold"), fill=MUTED, anchor="rm")
    return img


def _section(g: dict, s: dict, n: int, idx: int, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _header(d, f"{n:02d}  {g['category']}", f"{idx} / {total}")
    t = font(116, "Title")
    y = 220
    for line in wrap(d, _t(s.get("card_title") or s["heading"]), t, W - PAD * 2 - 20, 2):
        _marked(d, PAD, y, line, t)
        y += 148
    y += 60
    d.line([(PAD, y), (W - PAD, y)], fill=LINE, width=3)
    y += 90
    pts = s.get("card") or []
    for size in (56, 52, 48, 44, 40, 36):  # 남은 공간에 맞게 글자 크기 조절
        f = font(size, "Medium")
        wrapped = [wrap(d, p, f, W - PAD * 2 - 70, 3) for p in pts]
        need = sum(len(w) * int(size * 1.5) + 70 for w in wrapped)
        if y + need <= H - 160:
            break
    lh = int(size * 1.5)
    for i, w in enumerate(wrapped, 1):
        d.text((PAD, y), f"{i}", font=font(size, "ExtraBold"), fill=INK)
        for line in w:
            d.text((PAD + 70, y), line, font=f, fill=SUB)
            y += lh
        y += 70
    d.text((W / 2, H - 80), "자세한 내용은 프로필 링크(블로그)에서", font=font(28, "Medium"), fill=MUTED, anchor="mm")
    return img


def _closing(g: dict, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _header(d, BRAND, f"{total} / {total}")
    t = font(110, "Title")
    d.text((PAD, 260), "저장해두고", font=t, fill=INK)
    _marked(d, PAD, 400, "꺼내보세요", t)
    y = 620
    for line in wrap(d, g.get("closing") or g["comment"], font(42, "Medium"), W - PAD * 2, 6):
        d.text((PAD, y), line, font=font(42, "Medium"), fill=SUB)
        y += 64
    d.text((PAD, H - 140), "매일 탈임상 공고도 올라와요", font=font(40, "Title"), fill=INK, anchor="lm")
    d.text((PAD, H - 82), "프로필 링크에서 확인" + (f"  ·  @{HANDLE}" if HANDLE else ""), font=font(30, "Medium"), fill=MUTED, anchor="lm")
    return img


def thumb(g: dict) -> Image.Image:
    S, P = 1080, 90
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)
    d.text((P, 130), "탈임상 가이드", font=font(44, "Bold"), fill=MUTED)
    lines = [_t(x) for x in g["cover"]]
    size = 140 if max(len(x) for x in lines) <= 6 else 112
    t = font(size, "Title")
    y = 240
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            _marked(d, P, y, line, t)
        else:
            d.text((P, y), line, font=t, fill=INK)
        y += int(size * 1.3)
    d.line([(P, S - 200), (S - P, S - 200)], fill=LINE, width=3)
    d.text((P, S - 130), g["category"], font=font(44, "Bold"), fill=INK, anchor="lm")
    d.text((S - P, S - 130), BRAND, font=font(36, "Medium"), fill=MUTED, anchor="rm")
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
    gdir = docs / "guides"
    if not gdir.exists():
        return []
    items = []
    for d in sorted((p for p in gdir.iterdir() if p.is_dir()), reverse=True)[:30]:
        try:
            meta = json.loads((d / "guide.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {"title": "", "category": ""}
        items.append(f'<li><a href="guides/{d.name}/">{d.name}</a> <span class="muted">· {_e(meta["category"])}</span><br>{_e(meta["title"])}</li>')
    return items

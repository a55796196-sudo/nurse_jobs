"""매일 확인용 웹페이지 생성 (GitHub Pages, docs/ 폴더).

- 네이버 블로그에 붙여넣을 글 (복사 버튼)
- 인스타 캡션 (복사 버튼)
- 카드뉴스 이미지 미리보기/다운로드
"""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

from .models import CATEGORIES, Job
from .render import d_day

STYLE = """
:root{--bg:#f8fafc;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--accent:#2563eb}
@media (prefers-color-scheme:dark){:root{--bg:#0b1220;--card:#111a2e;--ink:#e2e8f0;--muted:#94a3b8;--line:#1e293b;--accent:#60a5fa}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;line-height:1.6}
main{max-width:860px;margin:0 auto;padding:24px 16px 80px}h1{font-size:1.6rem;margin:.2em 0}
.box{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:18px 0}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:space-between}
button{background:var(--accent);color:#fff;border:0;border-radius:10px;padding:10px 16px;font-size:1rem;font-weight:600;cursor:pointer}
button.done{background:#16a34a}.muted{color:var(--muted);font-size:.9rem}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}.cards img{width:100%;border-radius:8px;border:1px solid var(--line)}
pre{white-space:pre-wrap;background:var(--bg);padding:12px;border-radius:8px;font-family:inherit;margin:8px 0 0}
#post{background:#fff;color:#111;padding:16px;border-radius:8px;max-height:480px;overflow:auto}
a{color:var(--accent)}ul.days{padding-left:1.2em}
"""

SCRIPT = """
async function copyHtml(id, btn){
  const el=document.getElementById(id);
  try{await navigator.clipboard.write([new ClipboardItem({
    'text/html':new Blob([el.innerHTML],{type:'text/html'}),
    'text/plain':new Blob([el.innerText],{type:'text/plain'})})]);}
  catch(e){const r=document.createRange();r.selectNodeContents(el);const s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy');s.removeAllRanges();}
  done(btn);}
async function copyText(id, btn){
  const t=document.getElementById(id).innerText;
  try{await navigator.clipboard.writeText(t);}catch(e){}
  done(btn);}
function done(btn){const o=btn.textContent;btn.textContent='복사됨 ✓';btn.classList.add('done');setTimeout(()=>{btn.textContent=o;btn.classList.remove('done')},1500);}
"""


def _e(s) -> str:
    return html.escape(str(s or ""))


def blog_title(jobs: list[Job], today: date) -> str:
    roles = []
    for j in jobs:
        if j.job_role and j.job_role not in roles:
            roles.append(j.job_role)
    return f"[{today.month}/{today.day}] 탈임상 간호사 채용 {len(jobs)}건 ({', '.join(roles[:3])} 외)"


def blog_html(jobs: list[Job], today: date) -> str:
    """네이버 블로그 에디터에 붙여넣었을 때 서식이 유지되는 단순 HTML."""
    out = [
        f"<p>안녕하세요! {today.month}월 {today.day}일 새로 올라온 <b>탈임상 간호사 채용공고 {len(jobs)}건</b>을 정리했어요.</p>",
        "<p>병원 밖에서 일하고 싶은 간호사분들께 도움이 되길 바랍니다 :)</p><p>&nbsp;</p>",
    ]
    for cat, meta in CATEGORIES.items():
        group = [j for j in jobs if j.category == cat]
        if not group:
            continue
        out.append(f"<h2>{meta['emoji']} {cat} ({len(group)}건)</h2>")
        for j in group:
            out.append(f"<h3>{_e(j.org)} · {_e(j.title)}</h3><ul>")
            out.append(f"<li><b>직무</b>: {_e(j.job_role)}</li>")
            out.append(f"<li><b>마감</b>: {_e(d_day(j.deadline, today))}</li>")
            if j.location:
                out.append(f"<li><b>지역</b>: {_e(j.location)}</li>")
            if j.employment_type:
                out.append(f"<li><b>고용형태</b>: {_e(j.employment_type)}</li>")
            out.append("</ul>")
            if j.summary:
                out.append(f"<p>{_e(j.summary)}</p>")
            if j.requirements:
                out.append("<p><b>자격요건</b><br>" + "<br>".join("· " + _e(r) for r in j.requirements) + "</p>")
            out.append(f'<p>👉 <a href="{_e(j.url)}">공고 원문 보기</a></p><p>&nbsp;</p>')
    out.append("<p>※ 공고 내용은 요약본이며, 지원 전 반드시 원문을 확인해주세요.</p>")
    tags = {"탈임상", "간호사채용", "간호사이직", "탈임상간호사"}
    for j in jobs:
        tags.update(t.replace(" ", "") for t in j.tags)
    out.append("<p>" + " ".join(f"#{_e(t)}" for t in list(tags)[:25]) + "</p>")
    return "\n".join(out)


def ig_caption(jobs: list[Job], today: date, limit: int = 9) -> str:
    lines = [f"📌 {today.month}/{today.day} 오늘의 탈임상 간호사 공고 {len(jobs)}건", ""]
    for j in jobs[:limit]:
        meta = CATEGORIES.get(j.category or "", {"emoji": "•"})
        lines.append(f"{meta['emoji']} {j.org} | {j.job_role} ({d_day(j.deadline, today).split(' ·')[0]})")
    if len(jobs) > limit:
        lines.append(f"…외 {len(jobs) - limit}건")
    lines += ["", "🔗 전체 공고와 원문 링크는 프로필 링크(블로그)에서 확인하세요!", "💾 저장해두고 지원 마감 놓치지 마세요", ""]
    tags = ["탈임상", "탈임상간호사", "간호사채용", "간호사이직", "간호사", "간호사취업",
            "보건교사", "산업간호사", "CRC", "간호직공무원", "공기업채용"]
    lines.append(" ".join("#" + t for t in tags))
    return "\n".join(lines)


def build_day(jobs: list[Job], today: date, docs: Path, card_paths: list[Path]) -> Path:
    day_dir = docs / today.isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    title = blog_title(jobs, today)
    imgs = "".join(f'<a href="{p.name}" download><img src="{p.name}" alt="카드 {i}"></a>' for i, p in enumerate(card_paths))
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{today.isoformat()} 탈임상 공고</title>
<style>{STYLE}</style></head><body><main>
<p class="muted"><a href="../">← 날짜 목록</a></p>
<h1>{today.isoformat()} 탈임상 공고 {len(jobs)}건</h1>

<div class="box"><div class="row"><b>① 네이버 블로그 제목</b><button onclick="copyText('t',this)">제목 복사</button></div>
<pre id="t">{_e(title)}</pre></div>

<div class="box"><div class="row"><b>② 네이버 블로그 본문</b><button onclick="copyHtml('post',this)">본문 복사</button></div>
<p class="muted">복사 후 네이버 블로그 글쓰기 화면에 붙여넣기(Ctrl+V)만 하면 돼요.</p>
<div id="post">{blog_html(jobs, today)}</div></div>

<div class="box"><div class="row"><b>③ 인스타 카드뉴스</b><span class="muted">이미지를 눌러 저장</span></div>
<div class="cards">{imgs}</div></div>

<div class="box"><div class="row"><b>④ 인스타 캡션</b><button onclick="copyText('cap',this)">캡션 복사</button></div>
<pre id="cap">{_e(ig_caption(jobs, today))}</pre></div>
</main><script>{SCRIPT}</script></body></html>"""
    (day_dir / "index.html").write_text(page, encoding="utf-8")
    (day_dir / "caption.txt").write_text(ig_caption(jobs, today), encoding="utf-8")
    (day_dir / "jobs.json").write_text(json.dumps([j.to_dict() for j in jobs], ensure_ascii=False, indent=1), encoding="utf-8")
    return day_dir


def build_index(docs: Path) -> None:
    days = sorted((p.name for p in docs.iterdir() if p.is_dir() and p.name[:2] == "20"), reverse=True)
    items = []
    for d in days[:60]:
        try:
            n = len(json.loads((docs / d / "jobs.json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            n = "?"
        items.append(f'<li><a href="{d}/">{d}</a> <span class="muted">· {n}건</span></li>')
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>탈임상 공고 작업실</title>
<style>{STYLE}</style></head><body><main><h1>탈임상 공고 작업실</h1>
<p class="muted">매일 아침 자동으로 업데이트됩니다. 날짜를 눌러 블로그 글과 카드뉴스를 확인하세요.</p>
<div class="box"><ul class="days">{''.join(items) or '<li>아직 데이터가 없어요</li>'}</ul></div>
</main></body></html>"""
    (docs / "index.html").write_text(page, encoding="utf-8")
    (docs / ".nojekyll").write_text("", encoding="utf-8")

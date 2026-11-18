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
from .blog import BLOG_CATEGORY, SUMMARY_CATEGORY, _emp, _org, blog_tags, picks, post_html, post_title, summary_html, summary_title
from .render import summary_thumb, thumb

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
#post,.post{background:#fff;color:#111;padding:16px;border-radius:8px;}
h2{font-size:1.2rem;margin:28px 0 4px}
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


def ig_caption(job: Job, today: date) -> str:
    """인스타 게시물 1개(공고 1개)용 캡션."""
    dl = d_day(job.deadline, today).split(" ·")[0]
    when = f"{int(job.deadline[5:7])}/{int(job.deadline[8:10])}" + (f" {job.deadline_time}" if job.deadline_time else "") if job.deadline else "상시"
    role = " ".join(x for x in (job.department, job.job_role) if x)
    import re
    lines = [f"📌 {re.sub(r'^\(.*?\)\s*', '', post_title(job))}", ""]
    lines.append(f"📍 근무지: {job.location or '공고 확인'}")
    lines.append(f"⏰ 마감: {when}까지 ({dl})")
    if job.salary:
        lines.append(f"💰 급여: {job.salary}")
    if job.work_hours:
        lines.append(f"🕘 근무: {job.work_hours}")
    if job.requirements:
        lines.append("✅ 자격: " + " / ".join(job.requirements[:3]))
    if job.ig_tip or job.summary:
        lines += ["", "💡 " + (job.ig_tip or job.summary)]
    lines += ["", "🔗 우대 사항·전형·지원 링크는 프로필 링크(블로그)에서", "💾 저장해두고 마감 체크", ""]
    tags = ["탈임상", "탈임상간호사", "간호사채용", "간호사이직", "간호사취업"]
    tags += [t.replace(" ", "") for t in (job.tags or [])][:6]
    lines.append(" ".join("#" + t for t in dict.fromkeys(tags)))
    return "\n".join(lines)


def build_day(jobs: list[Job], today: date, docs: Path, card_paths: list[list[Path]], all_open: list[Job] | None = None) -> Path:
    day_dir = docs / today.isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    title = blog_title(jobs, today)
    ig = []
    for n, (j, ps) in enumerate(zip(picks(jobs), card_paths), start=1):
        imgs = "".join(f'<a href="{p.name}" download><img src="{p.name}" alt="인스타 {n}-{k}" style="width:150px;border-radius:8px;border:1px solid var(--line);margin:0 6px 6px 0"></a>' for k, p in enumerate(ps, start=1))
        ig.append(f"""<div class="box"><div style="display:flex;flex-wrap:wrap">{imgs}</div>
<div><b>인스타 {n}. {_e(j.org)}</b> <span class="muted">({len(ps)}장 · 순서대로 올리세요)</span>
<pre id="ic{n}" style="margin:8px 0">{_e(ig_caption(j, today))}</pre>
<button onclick="copyText('ic{n}',this)">캡션 복사</button></div></div>""")
    ig_html = ("<h2>📷 인스타 게시물 (공고 1개 = 1장)</h2>\n" + "".join(ig)) if ig else ""
    posts = []
    for n, j in enumerate(picks(jobs), start=1):
        role = " ".join(x for x in (j.department, j.job_role) if x)
        loc = (j.location or "").replace(",", " · ")
        emp_txt = _emp(j) + (" (상근)" if (j.work_hours or "").startswith("상근") else "")
        thumb(_org(j), role, j.deadline, j.deadline_time, loc, emp_txt).save(day_dir / f"thumb-{n:02d}.png")
        tags = " ".join("#" + t for t in blog_tags(j))
        posts.append(f"""<div class="box"><div class="row"><b>글 {n}. {_e(j.org)} · {_e(j.job_role)}</b>
<span class="muted">카테고리: {_e(BLOG_CATEGORY.get(j.category or '', '탈임상 채용공고'))}</span></div>
<div class="row" style="margin-top:8px"><pre id="pt{n}" style="flex:1;margin:0">{_e(post_title(j))}</pre>
<button onclick="copyText('pt{n}',this)">제목 복사</button></div>
<details open><summary class="muted" style="margin:10px 0;cursor:pointer">본문 미리보기 (접기)</summary>
<div id="pb{n}" class="post">{post_html(j, today)}</div></details>
<div class="row"><span class="muted">네이버 글쓰기에 제목 → 본문 순서로 붙여넣으세요</span>
<button onclick="copyHtml('pb{n}',this)">본문 복사</button></div>
<div class="row" style="margin-top:10px"><pre id="tg{n}" style="flex:1;margin:0">{_e(tags)}</pre>
<button onclick="copyText('tg{n}',this)">태그 복사</button></div>
<div class="row" style="margin-top:10px;align-items:flex-start"><a href="thumb-{n:02d}.png" download><img src="thumb-{n:02d}.png" alt="썸네일 {n}" style="width:160px;border-radius:8px;border:1px solid var(--line)"></a>
<span class="muted">썸네일: 이미지를 눌러 저장 후 글 맨 위에 넣으세요</span></div></div>""")
    open_jobs = all_open if all_open is not None else [j for j in jobs if j.is_target]
    cats = [(c, c) for c in CATEGORIES]
    soon_n = sum(1 for j in open_jobs if j.deadline and (date.fromisoformat(j.deadline) - today).days <= 3)
    summary_thumb(today, len(open_jobs), [(n, sum(1 for j in open_jobs if j.category == c)) for c, n in cats], soon_n).save(day_dir / "thumb-summary.png")
    posts_html = "".join(posts) or '<div class="box"><p class="muted">오늘은 개별 글로 올릴 공고가 없어요.</p></div>'
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{today.isoformat()} 탈임상 공고</title>
<style>{STYLE}</style></head><body><main>
<p class="muted"><a href="../">← 날짜 목록</a></p>
<h1>{today.isoformat()} 탈임상 공고 {len(jobs)}건</h1>

<h2>📝 오늘 올릴 블로그 글 {len(picks(jobs))}개</h2>
{posts_html}

<h2>📋 진행 중 공고 전체 정리 (1개)</h2>
<div class="box"><div class="row"><b>전체 정리 글</b><span class="muted">카테고리: {SUMMARY_CATEGORY}</span></div>
<div class="row" style="margin-top:8px"><pre id="st" style="flex:1;margin:0">{_e(summary_title(open_jobs, today))}</pre>
<button onclick="copyText('st',this)">제목 복사</button></div>
<details><summary class="muted" style="margin:10px 0;cursor:pointer">본문 미리보기</summary>
<div id="sb" class="post">{summary_html(open_jobs, today)}</div></details>
<div class="row"><span class="muted">이 글은 매일 새로 올리거나, 기존 글을 수정해서 갱신해도 돼요</span>
<button onclick="copyHtml('sb',this)">본문 복사</button></div>
<div class="row" style="margin-top:10px;align-items:flex-start"><a href="thumb-summary.png" download><img src="thumb-summary.png" alt="정리 썸네일" style="width:160px;border-radius:8px;border:1px solid var(--line)"></a>
<span class="muted">썸네일: 이미지를 눌러 저장</span></div></div>

{ig_html}

</main><script>{SCRIPT}</script></body></html>"""
    (day_dir / "index.html").write_text(page, encoding="utf-8")
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

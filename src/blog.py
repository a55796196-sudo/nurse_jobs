"""공고별 네이버 블로그 글 생성.

네이버 에디터에 붙여넣었을 때 서식이 유지되도록 단순한 HTML(h2/h3/p/ul/b/a)만 사용한다.
"""
from __future__ import annotations

import html
from datetime import date

from .models import Job
from .render import d_label

AUTHOR = "리브"

# 블로그 카테고리 (네이버 블로그에 만든 이름과 같아야 함)
BLOG_CATEGORY = {
    "공공": "탈임상 채용공고 > 공공기관·공무원",
    "학교": "탈임상 채용공고 > 보건교사",
    "기업": "탈임상 채용공고 > 산업간호사·기업",
    "연구": "탈임상 채용공고 > 임상연구",
}


def _e(s) -> str:
    return html.escape(str(s or "")).strip()


def _md(d: date) -> str:
    return f"{d.month}월 {d.day}일"


def _org(job: Job) -> str:
    return job.org.replace("(주)", "").strip()


def post_title(job: Job) -> str:
    """검색용 제목: 기관명 + 직무 + '채용' + 정리 키워드."""
    year = (job.deadline or "")[:4] or str(date.today().year)
    return f"{_org(job)} {job.job_role} 채용 {year} | 지원자격·마감일 정리"


def post_html(job: Job, today: date) -> str:
    label, dl = d_label(job.deadline, today)
    period = ""
    if job.start_date and dl:
        period = f"{_md(date.fromisoformat(job.start_date))} ~ {_md(dl)}"
    elif dl:
        period = f"~ {_md(dl)}"
    else:
        period = "상시 (채용 시 마감)"

    out: list[str] = []
    out.append(f"<p>안녕하세요, 탈임상 채용노트 {AUTHOR}예요 :)</p>")
    out.append(f"<p>오늘은 <b>{_e(_org(job))} {_e(job.job_role)}</b> 채용 공고를 정리해봤어요.</p>")
    if job.summary:
        out.append(f"<p>{_e(job.summary)}</p>")
    out.append("<p>&nbsp;</p>")

    # 한눈에 보기
    out.append("<h2>📌 한눈에 보기</h2><ul>")
    rows = [
        ("기관", _org(job)),
        ("직무", job.job_role),
        ("고용형태", job.employment_type),
        ("근무지", job.location),
        ("모집인원", job.headcount),
        ("접수기간", period),
    ]
    for k, v in rows:
        if v:
            out.append(f"<li><b>{k}</b> : {_e(v)}</li>")
    if dl:
        out.append(f"<li><b>마감</b> : {_md(dl)} ({label})</li>")
    out.append("</ul><p>&nbsp;</p>")

    quals = job.qualifications or job.requirements
    if quals:
        out.append("<h2>✅ 지원 자격</h2><ul>")
        out += [f"<li>{_e(q)}</li>" for q in quals]
        out.append("</ul><p>&nbsp;</p>")

    if job.preferred:
        out.append("<h2>⭐ 우대 사항</h2><ul>")
        out += [f"<li>{_e(q)}</li>" for q in job.preferred]
        out.append("</ul><p>&nbsp;</p>")

    if job.process:
        out.append(f"<h2>🧭 전형 절차</h2><p>{_e(job.process)}</p><p>&nbsp;</p>")

    out.append("<h2>✍️ 자기소개서 항목</h2>")
    out.append("<p>자기소개서 문항은 공고문 첨부파일에 있어요. 아래 원문 링크에서 첨부된 공고문을 꼭 확인해주세요.</p><p>&nbsp;</p>")

    out.append("<h2>🔗 지원 방법</h2>")
    out.append(f'<p>👉 <a href="{_e(job.url)}">공고 원문 바로가기</a></p>')
    out.append("<p>※ 이 글은 공고 내용을 요약한 거예요. 지원 전 원문 공고를 꼭 확인해주세요.</p><p>&nbsp;</p>")

    if job.blog_comment:
        out.append(f"<h2>💬 {AUTHOR}의 한마디</h2><p>{_e(job.blog_comment)}</p><p>&nbsp;</p>")

    out.append("<p>병원 밖 간호사 채용 공고는 매일 정리해서 올리고 있어요. 이웃추가 해두시면 놓치지 않으실 거예요!</p>")

    tags = ["탈임상", "탈임상간호사", "간호사채용", "간호사이직", f"{_org(job).replace(' ', '')}채용"]
    for t in job.tags:
        t = t.replace(" ", "").lstrip("#")
        if t and t not in tags:
            tags.append(t)
    out.append("<p>" + " ".join(f"#{_e(t)}" for t in tags[:12]) + "</p>")
    return "\n".join(out)


def picks(jobs: list[Job]) -> list[Job]:
    """오늘 개별 글로 올릴 공고 (마감 빠른 순)."""
    return sorted([j for j in jobs if j.is_target and j.blog_pick], key=lambda j: j.deadline or "9999")

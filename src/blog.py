"""공고별 네이버 블로그 글 생성.

네이버 에디터에 붙여넣었을 때 서식이 유지되도록 단순한 HTML(h2/h3/p/ul/b/a)만 사용한다.
"""
from __future__ import annotations

import html
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

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
    return re.sub(r"^\((재|사|주)\)|\(주\)|㈜", "", job.org).strip()


def _emp(job: Job) -> str:
    """제목용 고용형태: 공고 제목에 쓰인 표현을 우선 (예: 대체인력 계약직)."""
    words = [w for w in ("무기계약직", "정규직", "대체인력", "기간제", "계약직", "인턴") if w in job.title]
    if "무기계약직" in words and "계약직" in words:
        words.remove("계약직")
    if words:
        return " ".join(words[:2])
    t = (job.employment_type or "").split(",")[0].strip()
    return {"비정규직": "계약직"}.get(t, t)


def post_title(job: Job) -> str:
    """예: (~12/1) 국민건강보험공단 일산병원 간호행정부 간호사 기간제 채용"""
    dl = f"(~{int(job.deadline[5:7])}/{int(job.deadline[8:10])}) " if job.deadline else "(상시) "
    role = job.job_role or ""
    if job.department and job.department not in role:
        role = f"{job.department} {role}"
    emp = "" if "강사" in role else _emp(job)
    if emp and emp in role:
        emp = ""
    tail = "" if ("간호" in role or "보건" in role) else " (간호사 지원 가능)"
    return " ".join(f"{dl}{_org(job)} {role.strip()} {emp} 채용".split()) + tail


def _x(job: Job, key: str) -> str:
    return str(job.extra.get(key) or "").strip()


def _lines(text: str) -> list[str]:
    """API 원문(줄바꿈·· 기호 섞인 텍스트)을 항목 목록으로."""
    out = []
    for ln in text.replace("\r", "").split("\n"):
        ln = ln.strip(" ·-•ㅁ○*\t")
        if len(ln) > 1:
            out.append(ln)
    return out


NEED = "공고문 확인 필요"


def _is_site_home(url: str) -> bool:
    """공고 상세가 아니라 채용 사이트 첫 화면 주소인지 (경로·번호가 없으면 첫 화면으로 봄)."""
    from urllib.parse import urlparse
    u = urlparse(url or "")
    path = u.path.strip("/")
    return not u.query and (not path or not any(c.isdigit() for c in path))
SALARY_FILE = Path(__file__).resolve().parent.parent / "data" / "alio_salary.json"


@lru_cache(maxsize=1)
def _salary_db() -> dict:
    try:
        return json.loads(SALARY_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# 의료기관은 의사·간호사(교대)·행정직 급여가 한 숫자에 섞여 있어 초임·평균보수가 참고가 안 됨
MEDICAL_ORG = ("병원", "의료원", "의학원", "암센터", "혈액원")


def salary_ref(job: Job) -> dict | None:
    """알리오 경영공시 기관별 초임·평균보수 (천원 단위).
    공고에 급여가 있거나 의료기관이면 쓰지 않는다."""
    if job.salary or any(k in job.org for k in MEDICAL_ORG):
        return None
    orgs = _salary_db().get("orgs", {})
    base = re.sub(r"^\((재|사|주)\)|\((재|사|주)\)$|㈜", "", job.org).strip()
    for name in (job.org, base, base + "(주)", "(재)" + base, "(사)" + base):
        if name in orgs:
            return orgs[name]
    return None


def _manwon(thousand: int) -> str:
    return f"약 {round(thousand / 10):,}만 원"


def post_html(job: Job, today: date) -> str:
    label, dl = d_label(job.deadline, today)
    if job.start_date and dl:
        period = f"{_md(date.fromisoformat(job.start_date))} ~ {_md(dl)} ({label})"
    elif dl:
        period = f"~ {_md(dl)} ({label})"
    else:
        period = "상시 (채용 시 마감)"
    headcount = job.headcount or (f"{_x(job, 'recrutNope')}명" if _x(job, "recrutNope") not in ("", "0") else NEED)

    rows = [
        ("기관", _org(job)),
        ("부서 · 직무", " ".join(x for x in (job.department, job.job_role) if x)),
        ("채용 인원", headcount),
        ("고용 형태", job.employment_type or NEED),
        ("구분", _x(job, "recrutSeNm") or NEED),
        ("근무지", job.location or NEED),
        ("학력", (_x(job, "acbgCondNmLst") if _x(job, "acbgCondNmLst").count(",") < 2 else "분야별 상이 (지원 자격 참고)") or NEED),
        ("급여", job.salary or (f"{NEED} (아래 경영공시 참고)" if salary_ref(job) else f"{NEED} (기관 내규)")),
        ("근무 시간", job.work_hours or NEED),
        ("접수 기간", period),
    ]

    out: list[str] = []
    out.append(f"<p><b>{_e(post_title(job))}</b> 공고 정리예요. 지원 전 원문 공고문도 꼭 확인해주세요.</p><p>&nbsp;</p>")

    out.append("<h2>📌 채용 개요</h2>")
    out.append('<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">')
    keep = {"급여", "근무 시간"}  # 없어도 '확인 필요'로 보여줄 항목
    for k, v in rows:
        if (not v or v == NEED) and k not in keep:
            continue
        out.append(f'<tr><td style="width:30%;background:#f5f5f5"><b>{k}</b></td><td>{_e(v)}</td></tr>')
    out.append("</table><p>&nbsp;</p>")

    ref = salary_ref(job)
    if ref:
        year = _salary_db().get("year", "")
        out.append(f"<h2>💰 이 기관 연봉 참고 ({year}년 알리오 경영공시)</h2><ul>")
        if ref.get("starting"):
            out.append(f"<li><b>정규직 신입사원 초임</b> : {_manwon(ref['starting'])}</li>")
        if ref.get("avg"):
            out.append(f"<li><b>정규직 직원 평균보수</b> : {_manwon(ref['avg'])}</li>")
        if ref.get("avg_mugi"):
            out.append(f"<li><b>무기계약직 평균보수</b> : {_manwon(ref['avg_mugi'])}</li>")
        if ref.get("tenure_months"):
            out.append(f"<li><b>정규직 평균 근속</b> : 약 {ref['tenure_months'] // 12}년 {ref['tenure_months'] % 12}개월</li>")
        out.append("</ul><p>※ 기관 전체 기준 공시 금액이에요. 이 공고의 직무·고용형태 급여와는 다를 수 있어요.</p><p>&nbsp;</p>")

    quals = job.qualifications or job.requirements or _lines(_x(job, "aplyQlfcCn"))
    if quals:
        out.append("<h2>✅ 지원 자격</h2><ul>" + "".join(f"<li>{_e(q)}</li>" for q in quals[:8]) + "</ul><p>&nbsp;</p>")

    pref = job.preferred or _lines(_x(job, "prefCn"))
    if pref:
        out.append("<h2>⭐ 우대 사항</h2><ul>" + "".join(f"<li>{_e(q)}</li>" for q in pref[:8]) + "</ul><p>&nbsp;</p>")

    steps = _lines(job.process or _x(job, "scrnprcdrMthdExpln"))
    if steps:
        out.append("<h2>🧭 전형 절차</h2><ol>" + "".join(f"<li>{_e(x)}</li>" for x in steps[:8]) + "</ol><p>&nbsp;</p>")
    if job.benefits:
        out.append("<h2>🎁 복리후생</h2><ul>" + "".join(f"<li>{_e(b)}</li>" for b in job.benefits) + "</ul><p>&nbsp;</p>")

    files = job.extra.get("files") or []
    out.append("<h2>📎 제출 서류 · 자소서</h2><ul>")
    if files:
        out.append("<li>첨부 파일: " + ", ".join(_e(f) for f in files) + "</li>")
    out.append("<li>자기소개서 문항: 공고 첨부 공고문·입사지원서 양식에 있어요</li>")
    missing = [k for k, ok in (("전형 절차", steps), ("복리후생", job.benefits)) if not ok]
    if missing:
        out.append(f"<li>{'·'.join(missing)}: 공고문에서 확인해주세요</li>")
    out.append("</ul><p>&nbsp;</p>")

    if job.faq:
        out.append("<h2>❓ 자주 궁금한 점</h2>")
        for q, a in job.faq:
            out.append(f"<p><b>Q. {_e(q)}</b><br>A. {_e(a)}</p>")
        out.append("<p>&nbsp;</p>")

    if job.blog_comment:
        out.append(f"<h2>💬 {AUTHOR}의 한마디</h2><p>{_e(job.blog_comment)}</p><p>&nbsp;</p>")

    out.append("<h2>🔗 지원하기</h2><ul>")
    alio = job.extra.get("alio_url") or (f"https://job.alio.go.kr/recruitview.do?idx={job.source_id}" if job.source == "alio" else "")
    if alio:
        out.append(f'<li><a href="{_e(alio)}">이 공고 원문 보기 (잡알리오 · 공고문·첨부파일)</a></li>')
    if _is_site_home(job.url):
        out.append(f'<li><a href="{_e(job.url)}">{_e(_org(job))} 채용 홈페이지</a> → 공고 목록에서 <b>"{_e(job.title)}"</b>을 찾아 지원하세요</li>')
    else:
        out.append(f'<li><a href="{_e(job.url)}">기관 채용 홈페이지에서 바로 지원</a></li>')
    out.append("</ul><p>※ 공고 내용을 요약한 글이에요. 급여·근무조건 등 세부 내용은 원문 공고문을 확인해주세요.</p><p>&nbsp;</p>")

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

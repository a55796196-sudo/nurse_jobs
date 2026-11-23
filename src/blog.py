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
    "기타": "탈임상 채용공고 > 기타",
}


def _e(s) -> str:
    return html.escape(str(s or "")).strip()


def _md(d: date) -> str:
    return f"{d.month}월 {d.day}일"


def _org(job: Job) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^\((재|사|주)\)|\(주\)|㈜|주식회사", "", job.org)).strip()


EMP_WORDS = (  # (찾는 말, 제목에 쓸 말) — 제목에는 고용형태 한 단어만
    ("무기계약", "무기계약직"), ("임기제", "임기제"), ("비정규직", "계약직"), ("정규직", "정규직"),
    ("기간제", "기간제"), ("계약직", "계약직"), ("대체인력", "대체인력"), ("인턴", "인턴"),
)


def _title_emp(job: Job) -> str:
    """제목용 고용형태 한 단어. 공고 제목 → 고용형태 칸 순서로, 가장 먼저 나온 표현을 쓴다
    (예: '정규직(수습 3개월) 또는 계약직(1년)' → 정규직, '지방시간선택제임기제 마급' → 임기제)."""
    for text in (job.title, job.employment_type or ""):
        hits = []
        for key, word in EMP_WORDS:
            i = text.find(key)
            if i < 0:
                continue
            if key == "정규직" and text[max(0, i - 1):i] == "비":   # '비정규직' 안의 '정규직'
                rest = text.replace("비정규직", "")
                i = rest.find("정규직")
                if i < 0:
                    continue
            hits.append((i, word))
        if hits:
            return min(hits)[1]
    return ""


def _emp(job: Job) -> str:
    """제목용 고용형태: 공고 제목에 쓰인 표현을 우선 (예: 대체인력 계약직)."""
    title = job.title.replace("비정규직", " ")  # '비정규직' 안의 '정규직'을 정규직으로 읽지 않게
    words = [w for w in ("무기계약직", "정규직", "대체인력", "기간제", "계약직", "인턴") if w in title]
    if "비정규직" in job.title and not any(w in words for w in ("기간제", "계약직", "무기계약직")):
        words.append("비정규직")
    if "무기계약직" in words and "계약직" in words:
        words.remove("계약직")
    if words:
        return " ".join(words[:2])
    t = (job.employment_type or "").split(",")[0].strip()
    return {"비정규직": "계약직"}.get(t, t)


METRO = ("서울", "인천", "부산", "대구", "대전", "광주", "울산", "세종", "제주")


def region(job: Job) -> str:
    """제목용 지역: 서울·광역시는 시도명, 도는 시·군 이름 (예: 경기 평택시 → 평택, 서울 강서구 → 서울)."""
    loc = (job.location or "").split(",")[0].strip()
    parts = loc.split()
    if not parts:
        return ""
    if parts[0] in METRO or len(parts) == 1:
        return parts[0]
    city = parts[1]
    if city.endswith("구"):          # 도 + 구 (잘못 들어온 값 등)는 도 이름으로
        return parts[0]
    if city[-1] in "시군" and len(city) > 2:
        city = city[:-1]
    return city


def post_title(job: Job) -> str:
    """예: [고양] 국민건강보험공단 일산병원 간호행정부 간호사 기간제 채용 (~12/1)
    검색어가 '지역 + 직무 + 간호사 채용' 형태라 지역을 앞에, 마감일을 뒤에 둔다."""
    dl = f"(~{int(job.deadline[5:7])}/{int(job.deadline[8:10])})" if job.deadline else "(상시)"
    role = (job.job_role or "").strip()
    if job.department and job.department not in role:
        role = f"{job.department} {role}"
    emp = "" if "강사" in role else _title_emp(job)
    if emp and emp in role:
        emp = ""
    if "간호" not in role and "교사" not in role:
        role += "(간호사)" if "보건" in role else "(간호사 지원 가능)"
    reg = region(job)
    head = f"[{reg}] " if reg else ""
    return " ".join(f"{head}{_org(job)} {role} {emp} 채용 {dl}".split())


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


def blog_tags(job: Job) -> list[str]:
    """네이버 태그 칸에 넣을 태그 (5~10개)."""
    tags = [f"{_org(job).replace(' ', '')}채용", "간호사채용", "탈임상", "탈임상간호사"]
    for t in job.tags:
        t = t.replace(" ", "").lstrip("#")
        if t and t not in tags:
            tags.append(t)
    for t in ("간호사이직", "공공기관채용" if job.category == "공공" else "", "보건교사채용" if job.category == "학교" else ""):
        if t and t not in tags:
            tags.append(t)
    return tags[:10]


def post_html(job: Job, today: date) -> str:
    label, dl = d_label(job.deadline, today)
    tm = f" {job.deadline_time}" if job.deadline_time else ""
    if job.start_date and dl:
        period = f"{_md(date.fromisoformat(job.start_date))} ~ {_md(dl)}{tm} ({label})"
    elif dl:
        period = f"~ {_md(dl)}{tm} ({label})"
    else:
        period = "상시 (채용 시 마감)"
    total = _x(job, "recrutNope")
    if job.headcount:
        headcount = job.headcount
    elif total not in ("", "0"):
        headcount = f"공고 전체 {total}명 (분야별 인원은 공고문 확인)" if len(set(job.extra.get("steps") or [])) > 1 else f"{total}명"
    else:
        headcount = NEED
    emp = job.employment_type or NEED
    if job.contract_period:
        emp = f"{emp} ({job.contract_period})"
    edu = job.education or (_x(job, "acbgCondNmLst") if _x(job, "acbgCondNmLst").count(",") < 2 else "")
    ref = salary_ref(job)
    rows = [
        ("기관", _org(job)),
        ("부서 · 직무", " ".join(x for x in (job.department, job.job_role) if x)),
        ("채용 인원", headcount),
        ("고용 형태", emp),
        ("구분", _x(job, "recrutSeNm")),
        ("근무지", job.address or job.location or NEED),
        ("학력", edu),
        ("급여", job.salary or (f"{NEED} (아래 경영공시 참고)" if ref else f"{NEED} (기관 내규)")),
        ("근무 시간", job.work_hours or NEED),
        ("접수 기간", period),
    ]

    out: list[str] = []
    intro = job.intro or job.summary or ""
    out.append(f"<p>{_e(intro)}</p><p>&nbsp;</p>")

    out.append("<h2>📌 채용 개요</h2>")
    out.append('<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">')
    keep = {"급여", "근무 시간"}  # 없어도 '확인 필요'로 보여줄 항목
    for k, v in rows:
        if (not v or v == NEED) and k not in keep:
            continue
        out.append(f'<tr><td style="width:30%;background:#f5f5f5"><b>{k}</b></td><td>{_e(v)}</td></tr>')
    out.append("</table><p>&nbsp;</p>")

    if job.salary_detail:
        out.append("<h2>💰 급여</h2><ul>" + "".join(f"<li>{_e(x)}</li>" for x in job.salary_detail) + "</ul><p>&nbsp;</p>")
    elif ref:
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
        out.append("</ul><p>※ 기관 전체 기준 공시 금액입니다. 이 공고의 직무·고용형태 급여와 다를 수 있습니다.</p><p>&nbsp;</p>")

    if job.benefits:
        out.append("<h2>🎁 복리후생</h2><ul>" + "".join(f"<li>{_e(b)}</li>" for b in job.benefits) + "</ul><p>&nbsp;</p>")

    quals = job.qualifications or job.requirements or _lines(_x(job, "aplyQlfcCn"))
    if quals:
        out.append("<h2>✅ 지원 자격</h2><ul>" + "".join(f"<li>{_e(q)}</li>" for q in quals[:8]) + "</ul><p>&nbsp;</p>")

    pref = job.preferred or _lines(_x(job, "prefCn"))
    if pref:
        out.append("<h2>⭐ 우대 사항</h2><ul>" + "".join(f"<li>{_e(q)}</li>" for q in pref[:8]) + "</ul><p>&nbsp;</p>")

    if job.duties:
        out.append("<h2>📎 직무내용</h2><ul>" + "".join(f"<li>{_e(d)}</li>" for d in job.duties[:10]) + "</ul><p>&nbsp;</p>")

    steps = _lines(job.process or _x(job, "scrnprcdrMthdExpln"))
    if steps:
        out.append("<h2>🧭 전형 절차</h2><ol>" + "".join(f"<li>{_e(x)}</li>" for x in steps[:8]) + "</ol><p>&nbsp;</p>")

    tip = job.ig_tip or job.blog_comment
    if tip:
        out.append(f"<h2>💡 한줄 TIP</h2><p>{_e(tip)}</p><p>&nbsp;</p>")

    out.append("<h2>🔗 지원하기</h2><ul>")
    alio = job.extra.get("alio_url") or (f"https://job.alio.go.kr/recruitview.do?idx={job.source_id}" if job.source == "alio" else "")
    if alio:
        out.append(f'<li><a href="{_e(alio)}">이 공고 원문 보기 (잡알리오 · 공고문·첨부파일)</a></li>')
    if job.extra.get("search_hint"):
        out.append(f'<li><a href="{_e(job.url)}">경기도교육청 구인정보조회</a> → <b>"{_e(_org(job))}"</b> 검색 후 지원하세요</li>')
    elif _is_site_home(job.url):
        out.append(f'<li><a href="{_e(job.url)}">{_e(_org(job))} 채용 홈페이지</a> → 공고 목록에서 <b>"{_e(job.title)}"</b>을 찾아 지원하세요</li>')
    else:
        out.append(f'<li><a href="{_e(job.url)}">{"공고 원문 보기" if job.source == "gojobs" else "기관 채용 홈페이지에서 바로 지원"}</a></li>')
    if job.extra.get("apply"):
        out.append(f'<li>접수 방법: {_e(job.extra["apply"])}</li>')
    out.append("</ul><p>※ 공고 내용을 요약한 글입니다. 지원 전 원문 공고문을 꼭 확인하세요.</p><p>&nbsp;</p>")

    out.append("<p>" + " ".join(f"#{_e(t)}" for t in blog_tags(job)) + "</p>")
    return "\n".join(out)


def picks(jobs: list[Job]) -> list[Job]:
    """오늘 개별 글로 올릴 공고 (마감 빠른 순)."""
    return sorted([j for j in jobs if j.is_target and j.blog_pick], key=lambda j: j.deadline or "9999")


# ---------- 매일 '진행 중 공고 전체 정리' 글 (주간 채용 총정리 카테고리) ----------
SUMMARY_CATEGORY = "주간 채용 총정리"
CAT_ORDER = [("기업", "🏭 산업간호사·기업"), ("공공", "🏛️ 공공기관·공기업"), ("연구", "🔬 임상연구"), ("학교", "🏫 보건교사·학교 보건실"), ("기타", "🌏 기타")]


def summary_title(jobs: list[Job], today: date) -> str:
    return f"[{today.month}/{today.day}] 탈임상 간호사 채용공고 총정리 (진행 중 {len(jobs)}건)"


def _link(job: Job) -> str:
    return job.extra.get("alio_url") or job.url or ""


BLOG_ID = "live_in_fact"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read_json(name: str) -> dict:
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _blog_search(word: str) -> str:
    from urllib.parse import quote
    return f"https://blog.naver.com/PostSearchList.naver?blogId={BLOG_ID}&orderType=sim&searchText={quote(word)}"


def summary_html(jobs: list[Job], today: date) -> str:
    jobs = sorted(jobs, key=lambda j: j.deadline or "9999")
    seen, posted = _read_json("seen.json"), _read_json("posted.json")
    soon = [j for j in jobs if j.deadline and (date.fromisoformat(j.deadline) - today).days <= 3]

    def is_new(j: Job) -> bool:
        try:
            return (today - date.fromisoformat(seen.get(j.key, ""))).days <= 2
        except ValueError:
            return False

    n_new = sum(1 for j in jobs if is_new(j))
    out = [f"<p>{today.month}월 {today.day}일 기준, 지금 지원할 수 있는 <b>탈임상 간호사 채용공고 {len(jobs)}건</b>을 한 번에 정리했습니다."
           + (f" 새로 올라온 공고는 <b>{n_new}건</b>," if n_new else "")
           + (f" <b>3일 안에 마감</b>되는 공고는 <b>{len(soon)}건</b>입니다." if soon else "") + "</p>",
           "<p>🆕 새로 올라온 공고 · 📝 블로그에 자세한 정리글이 있는 공고 · 기관명을 누르면 공고 원문</p><p>&nbsp;</p>"]
    for cat, name in CAT_ORDER:
        group = [j for j in jobs if j.category == cat]
        if not group:
            continue
        out.append(f"<h2>{name} ({len(group)}건)</h2>")
        out.append('<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">')
        out.append('<tr style="background:#f5f5f5"><td><b>마감</b></td><td><b>기관 · 직무</b></td><td><b>근무지</b></td></tr>')
        merged: dict[tuple, list[Job]] = {}
        for j in group:  # 같은 기관·직무·지역·마감은 한 줄로
            role = " ".join(x for x in (j.department, j.job_role) if x) or j.title
            merged.setdefault((_org(j), role, j.location, j.deadline), []).append(j)
        for (_, role, _, _), same in merged.items():
            j = same[0]
            label, dl = d_label(j.deadline, today)
            when = f"{dl.month}/{dl.day}" if dl else "상시"
            urgent = dl is not None and (dl - today).days <= 3
            dcell = f"{_e(when)}<br>" + (f'<b><span style="color:#e03131">{_e(label)}</span></b>' if urgent else _e(label)) if dl else "상시"
            if len(same) > 1:
                role += f" ({len(same)}건)"
            emp = _title_emp(j)
            line2 = _e(role) + (f" · <b>{_e(emp)}</b>" if emp else "")
            new = "🆕 " if any(is_new(x) for x in same) else ""
            note = (f'<br>📝 <a href="{_e(_blog_search(_org(j)))}">정리글 보기</a>'
                    if any(x.key in posted for x in same) else "")
            out.append(f'<tr><td>{dcell}</td><td>{new}<a href="{_e(_link(j))}">{_e(_org(j))}</a><br>{line2}{note}</td>'
                       f'<td>{_e((j.location or "-").replace(",", " · "))}</td></tr>')
        out.append("</table><p>&nbsp;</p>")
    out.append("<p>📝 정리글에는 급여·자격요건·전형 절차·근무시간을 공고별로 자세히 정리해 두었습니다.</p>")
    out.append("<p>※ 마감일은 공고 기준이며, 조기 마감될 수 있으니 원문을 꼭 확인하세요.</p><p>&nbsp;</p>")
    out.append("<p>#탈임상 #탈임상간호사 #간호사채용 #간호사이직 #간호사채용공고 #공공기관채용 #보건교사채용 #채용공고총정리</p>")
    return "\n".join(out)

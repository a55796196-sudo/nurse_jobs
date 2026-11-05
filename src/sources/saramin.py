"""사람인 공식 Open API.

신청: oapi.saramin.co.kr 에서 API 이용 신청 (승인까지 며칠 걸릴 수 있음)
환경변수: SARAMIN_KEY
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import requests

from ..models import Job

ENDPOINT = "https://oapi.saramin.co.kr/job-search"
KST = timezone(timedelta(hours=9))

# 탈임상 직무를 찾기 위한 검색어. 결과에 섞인 병원 임상 공고는 AI가 걸러냄.
KEYWORDS = [
    "산업간호사", "보건관리자 간호사", "CRC 임상연구코디네이터", "CRA 간호사",
    "연구간호사", "보험심사 간호사", "손해사정 간호사", "제약 간호사",
    "헬스케어 간호사", "보건교사", "간호사 면허 사무직",
]


def _ts_to_date(ts) -> str | None:
    try:
        return datetime.fromtimestamp(int(ts), KST).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _name(d: dict | None, *path: str) -> str:
    for p in path:
        d = (d or {}).get(p)
    return str(d or "")


def fetch() -> list[Job]:
    key = (os.environ.get("SARAMIN_KEY") or "").strip()
    if not key:
        print("[saramin] SARAMIN_KEY 없음 → 건너뜀")
        return []

    seen: dict[str, Job] = {}
    for kw in KEYWORDS:
        resp = requests.get(
            ENDPOINT,
            params={"access-key": key, "keywords": kw, "count": 50, "sort": "pd"},
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        for it in (resp.json().get("jobs") or {}).get("job") or []:
            jid = str(it.get("id"))
            if jid in seen or str(it.get("active", "1")) != "1":
                continue
            pos = it.get("position") or {}
            title = _name(pos, "title")
            text = " / ".join(filter(None, [
                title,
                _name(pos, "job-code", "name"),
                _name(pos, "experience-level", "name"),
                _name(pos, "required-education-level", "name"),
                _name(it, "salary", "name"),
                str(it.get("keyword") or ""),
            ]))
            seen[jid] = Job(
                source="saramin",
                source_id=jid,
                title=title,
                org=_name(it, "company", "detail", "name"),
                url=it.get("url") or "",
                deadline=_ts_to_date(it.get("expiration-timestamp")),
                location=_name(pos, "location", "name").replace("&gt;", ">"),
                employment_type=_name(pos, "job-type", "name"),
                raw_text=text[:2000],
            )

    print(f"[saramin] {len(seen)}건")
    return list(seen.values())

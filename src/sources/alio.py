"""잡알리오(공공기관 채용정보) - 공공데이터포털 공식 API.

신청: data.go.kr 에서 '공공기관 채용정보 조회서비스' 검색 → 활용신청
환경변수: DATA_GO_KR_KEY (일반 인증키, Decoding 값)
"""
from __future__ import annotations

import os
import re

import requests

from ..models import Job

ENDPOINT = "https://apis.data.go.kr/1051000/recruitment/list"
NURSE_PATTERN = re.compile(r"간호|보건관리|보건직|보건교사|임상연구|CRC|CRA", re.I)


def _fmt_date(s: str | None) -> str | None:
    if not s:
        return None
    digits = re.sub(r"\D", "", s)[:8]
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}" if len(digits) == 8 else None


def fetch(max_pages: int = 5) -> list[Job]:
    key = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
    if not key:
        print("[alio] DATA_GO_KR_KEY 없음 → 건너뜀")
        return []

    jobs: list[Job] = []
    for page in range(1, max_pages + 1):
        resp = requests.get(
            ENDPOINT,
            params={
                "serviceKey": key,
                "pageNo": page,
                "numOfRows": 100,
                "resultType": "json",
                "ongoingYn": "Y",  # 진행 중인 공고만
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("result") or []
        if not items:
            break

        for it in items:
            text = " ".join(
                str(it.get(k) or "")
                for k in ("recrutPbancTtl", "ncsCdNmLst", "aplyQlfcCn", "prefCondCn", "recrutSeNm")
            )
            if not NURSE_PATTERN.search(text):
                continue
            jobs.append(
                Job(
                    source="alio",
                    source_id=str(it.get("recrutPblntSn")),
                    title=str(it.get("recrutPbancTtl") or "").strip(),
                    org=str(it.get("instNm") or "").strip(),
                    url=it.get("srcUrl") or f"https://job.alio.go.kr/recruitview.do?idx={it.get('recrutPblntSn')}",
                    deadline=_fmt_date(it.get("pbancEndYmd")),
                    location=it.get("workRgnNmLst"),
                    employment_type=it.get("hireTypeNmLst"),
                    raw_text=text[:2000],
                )
            )
        if len(items) < 100:
            break

    print(f"[alio] 간호 관련 {len(jobs)}건")
    return jobs

"""잡알리오(공공기관 채용정보) - 공공데이터포털 공식 API.

신청: data.go.kr 에서 '공공기관 채용정보 조회서비스' 검색 → 활용신청
환경변수: DATA_GO_KR_KEY (일반 인증키, Decoding 값)
"""
from __future__ import annotations

import os
import re

import time

import requests

from ..models import Job

ENDPOINTS = [
    "https://apis.data.go.kr/1051000/recruitment/list",
    "http://apis.data.go.kr/1051000/recruitment/list",
]


def _get(params: dict) -> requests.Response:
    """data.go.kr 은 가끔 응답이 느리거나 끊겨서 https/http 를 번갈아 재시도."""
    last: Exception | None = None
    for attempt in range(4):
        url = ENDPOINTS[attempt % 2]
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code} ({url.split(':')[0]}): {r.text[:300]}")
        except requests.RequestException as e:
            last = e
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"잡알리오 API 호출 실패: {last}")


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
        resp = _get(
            {
                "serviceKey": key,
                "pageNo": page,
                "numOfRows": 100,
                "resultType": "json",
                "ongoingYn": "Y",  # 진행 중인 공고만
            }
        )
        try:
            data = resp.json()
        except ValueError:  # 키 오류 등은 XML로 옴
            raise RuntimeError(f"예상과 다른 응답: {resp.text[:300]}")
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

"""Claude로 공고 분류·요약.

- 간호사 대상 '탈임상' 공고인지 판별 (병원 병동·외래 등 임상 공고는 제외)
- 4개 카테고리(공공/학교/기업/연구) 중 하나로 분류
- 2~3문장 요약 + 핵심 자격요건 추출

ANTHROPIC_API_KEY 가 없으면 키워드 규칙으로 대신 분류합니다(정확도 낮음).
"""
from __future__ import annotations

import json
import os
import re

from pydantic import BaseModel, ValidationError

from .models import CATEGORIES, Job

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
BATCH_SIZE = 10

SYSTEM = f"""너는 한국 간호사 커리어 채널의 공고 편집자야.
각 채용 공고를 보고 다음을 판단해.

1. is_target: 간호사 면허 소지자가 지원할 수 있는 '탈임상(병원 밖·비임상)' 공고면 true.
   - 병원 병동/외래/수술실/응급실/요양병원 간호사 같은 임상 근무는 false.
   - 병원 소속이라도 보험심사·QI·연구간호사·CRC처럼 환자 직접 간호가 아니면 true.
   - 간호사와 무관한 공고(일반 사무, 의사, 약사 전용 등)는 false.
2. category: {", ".join(f"{k}({v['desc']})" for k, v in CATEGORIES.items())} 중 하나. is_target이 false면 "제외".
3. job_role: 짧은 직무명 (예: 산업간호사, CRC, 간호직 공무원, 보건교사, 보험심사).
4. summary: 지원자 관점에서 2~3문장 한국어 요약. 공고에 없는 내용은 지어내지 마.
5. requirements: 핵심 자격요건 최대 3개 (짧게). 없으면 빈 배열.
6. tags: 검색용 해시태그 단어 최대 4개 (# 없이).
공고 원문에 없는 정보(연봉, 마감일 등)는 절대 추측하지 마."""


class Classified(BaseModel):
    id: str
    is_target: bool
    category: str
    job_role: str
    summary: str
    requirements: list[str]
    tags: list[str]


class BatchResult(BaseModel):
    results: list[Classified]


SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "is_target": {"type": "boolean"},
                    "category": {"type": "string", "enum": [*CATEGORIES.keys(), "제외"]},
                    "job_role": {"type": "string"},
                    "summary": {"type": "string"},
                    "requirements": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "is_target", "category", "job_role", "summary", "requirements", "tags"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}


def _apply(job: Job, c: Classified) -> None:
    job.is_target = c.is_target and c.category in CATEGORIES
    job.category = c.category if job.is_target else None
    job.job_role = c.job_role
    job.summary = c.summary
    job.requirements = c.requirements[:3]
    job.tags = c.tags[:4]


def _classify_batch_claude(client, jobs: list[Job]) -> None:
    import anthropic

    payload = [
        {"id": str(i), "title": j.title, "org": j.org, "location": j.location,
         "employment_type": j.employment_type, "deadline": j.deadline, "text": j.raw_text}
        for i, j in enumerate(jobs)
    ]
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            # 안전 분류기가 드물게 요청을 거절하면 다른 모델로 자동 재시도
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": "다음 공고들을 분류해줘:\n" + json.dumps(payload, ensure_ascii=False)}],
        )
    except anthropic.RateLimitError as e:
        print(f"[classify] 요청 한도 초과, 이 묶음은 다음 실행 때 다시 처리: {e}")
        return
    except anthropic.APIStatusError as e:
        print(f"[classify] API 오류 {e.status_code}: {e.message}")
        return
    except anthropic.APIConnectionError as e:
        print(f"[classify] 연결 오류: {e}")
        return

    if resp.stop_reason in ("refusal", "max_tokens"):
        print(f"[classify] 응답 중단({resp.stop_reason}) → 이 묶음 건너뜀")
        return
    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        result = BatchResult.model_validate_json(text)
    except ValidationError as e:
        print(f"[classify] 응답 형식 오류: {e}")
        return
    for c in result.results:
        if c.id.isdigit() and int(c.id) < len(jobs):
            _apply(jobs[int(c.id)], c)


# ---- API 키가 없을 때 쓰는 단순 키워드 분류 (테스트용) ----
_RULES = [
    ("연구", r"CRC|CRA|CRM|임상연구|연구간호|연구원|임상시험"),
    ("학교", r"보건교사|보건교육|학교"),
    ("공공", r"공단|공사|공무원|보건소|군무원|질병관리|심사평가원|공공|지자체|구청|시청|도청"),
    ("기업", r"산업간호|보건관리자|제약|보험|손해사정|헬스케어|의료기기|사내"),
]
_CLINICAL = r"병동|외래|수술실|응급실|중환자실|ICU|요양병원|간호조무|3교대|교대근무"


def _classify_rule(job: Job) -> None:
    text = f"{job.title} {job.org} {job.raw_text}"
    cat = next((c for c, p in _RULES if re.search(p, text, re.I)), None)
    job.is_target = bool(cat) and not re.search(_CLINICAL, text)
    job.category = cat if job.is_target else None
    job.job_role = job.job_role or (cat or "")
    job.summary = job.summary or f"{job.org} · {job.title}"


def classify(jobs: list[Job]) -> list[Job]:
    if not jobs:
        return jobs
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[classify] ANTHROPIC_API_KEY 없음 → 키워드 규칙으로 분류")
        for j in jobs:
            _classify_rule(j)
        return jobs

    import anthropic

    client = anthropic.Anthropic()
    for i in range(0, len(jobs), BATCH_SIZE):
        _classify_batch_claude(client, jobs[i : i + BATCH_SIZE])
    return jobs

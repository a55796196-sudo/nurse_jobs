"""공고 데이터 구조."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

# 탈임상 카테고리 4개 (인스타 가독성을 위해 고정)
CATEGORIES = {
    "공공": {"emoji": "🏛️", "color": "#2563EB", "desc": "공기업·공무원·보건소·군무원"},
    "학교": {"emoji": "🏫", "color": "#16A34A", "desc": "보건교사"},
    "기업": {"emoji": "🏭", "color": "#EA580C", "desc": "산업간호사·제약·보험심사·헬스케어"},
    "연구": {"emoji": "🔬", "color": "#9333EA", "desc": "CRC·CRA·연구간호사·연구기관"},
}


@dataclass
class Job:
    source: str            # 수집 출처 (alio, saramin ...)
    source_id: str         # 출처 안에서의 고유 ID
    title: str
    org: str               # 기관/회사명
    url: str
    deadline: Optional[str] = None   # YYYY-MM-DD
    location: Optional[str] = None
    employment_type: Optional[str] = None
    raw_text: str = ""     # AI 분류에 쓰는 원문 요약 텍스트

    # AI 분류 결과
    is_target: Optional[bool] = None     # 간호사 대상 탈임상 공고인가
    category: Optional[str] = None       # CATEGORIES 키
    job_role: Optional[str] = None       # 예: 산업간호사, CRC, 간호직 공무원
    summary: Optional[str] = None        # 2~3문장 한국어 요약
    requirements: list[str] = field(default_factory=list)  # 핵심 자격요건
    tags: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

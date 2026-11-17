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
    start_date: Optional[str] = None  # 접수 시작일 YYYY-MM-DD
    extra: dict = field(default_factory=dict)  # 출처 API 원본 항목 (모집인원·전형 등)

    # AI 분류 결과
    is_target: Optional[bool] = None     # 간호사 대상 탈임상 공고인가
    category: Optional[str] = None       # CATEGORIES 키
    job_role: Optional[str] = None       # 예: 산업간호사, CRC, 간호직 공무원
    summary: Optional[str] = None        # 2~3문장 한국어 요약
    requirements: list[str] = field(default_factory=list)  # 핵심 자격요건
    tags: list[str] = field(default_factory=list)

    # 블로그 글용 (blog_pick=True 인 공고만 채움)
    blog_pick: Optional[bool] = None     # 오늘 개별 블로그 글로 올릴 공고인가 (하루 3~5개)
    qualifications: list[str] = field(default_factory=list)  # 지원 자격 전체
    preferred: list[str] = field(default_factory=list)       # 우대 사항
    process: Optional[str] = None        # 전형 절차 (예: 서류 → 필기 → 면접)
    headcount: Optional[str] = None      # 모집 인원
    blog_comment: Optional[str] = None   # 리브의 한마디 (2~3문장, 이 공고만의 포인트)
    department: Optional[str] = None     # 소속 부서 (예: 간호행정부, 일차의료거점지원센터)
    salary: Optional[str] = None         # 급여 (원문에 있을 때만)
    work_hours: Optional[str] = None     # 근무시간·근무형태 (예: 09:00~18:00 / 3교대)
    benefits: list[str] = field(default_factory=list)  # 복리후생 (원문에 있을 때만)
    faq: list[list[str]] = field(default_factory=list)  # (사용 안 함, 예전 데이터 호환용)
    intro: Optional[str] = None          # 글 도입부 2~3문장 (공고마다 다르게)
    salary_detail: list[str] = field(default_factory=list)  # 💰 급여 칸: 연봉/일급, 월 환산, 포함·미포함 항목
    duties: list[str] = field(default_factory=list)         # 📎 직무내용
    contract_period: Optional[str] = None  # 계약기간 (예: 2027.01.18~2027.05.02)
    address: Optional[str] = None          # 상세 근무지 주소
    deadline_time: Optional[str] = None    # 마감 시각 (예: 16:00)
    education: Optional[str] = None        # 학력 조건만 (예: 학력무관, 학사 이상)

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

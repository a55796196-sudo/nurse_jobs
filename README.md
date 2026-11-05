# 병원 밖 간호사 · 탈임상 공고 자동화

매일 아침 6시 47분(한국시간)에 자동으로 실행됩니다.

1. **수집**: 잡알리오(공공기관), 사람인에서 간호사 관련 공고를 가져옴
2. **AI 분류**: Claude가 병원 임상 공고를 걸러내고 **공공 / 학교 / 기업 / 연구**로 분류, 요약
3. **콘텐츠 생성**: 인스타 카드뉴스(최대 10장) + 네이버 블로그 글 + 인스타 캡션
4. **작업실 페이지**: GitHub Pages에 매일 페이지가 생기고, 복사 버튼으로 블로그에 붙여넣기
5. **인스타 업로드**: 버튼 하나로 업로드 (원하면 완전 자동)

## 처음 한 번만 설정하기

### 1) API 키 등록
GitHub 저장소 → **Settings → Secrets and variables → Actions → New repository secret**

| 이름 | 어디서 받나요 | 필수 |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | ✅ (없으면 키워드 규칙으로 분류, 요약 없음) |
| `DATA_GO_KR_KEY` | data.go.kr → "공공기관 채용정보 조회서비스" 활용신청 → 일반 인증키(Decoding) | ✅ |
| `SARAMIN_KEY` | oapi.saramin.co.kr → API 이용 신청 | 권장 |
| `IG_USER_ID`, `IG_ACCESS_TOKEN` | 인스타 업로드용 (아래 4번) | 선택 |

같은 화면의 **Variables** 탭(공개 설정값):

| 이름 | 예시 |
|---|---|
| `BRAND_NAME` | 병원 밖 간호사 |
| `IG_HANDLE` | 인스타 아이디 (@ 빼고) |
| `PAGES_BASE_URL` | https://내아이디.github.io/nurse-jobs |
| `IG_AUTO_POST` | `true`면 매일 자동 업로드 (처음엔 비워두는 걸 추천) |

### 2) 작업실 페이지 켜기 (GitHub Pages)
Settings → **Pages** → Source: *Deploy from a branch* → Branch: `main`, 폴더: `/docs` → Save
→ 몇 분 뒤 `https://내아이디.github.io/nurse-jobs` 에서 확인

> 무료 계정에서 Pages를 쓰려면 저장소가 **Public**이어야 합니다. 키는 Secrets에 있어서 공개되지 않아요.

### 3) 첫 실행
**Actions** 탭 → "매일 탈임상 공고 수집" → **Run workflow**

### 4) 인스타 자동 업로드 (선택)
1. 인스타 앱 → 설정 → 계정 유형 및 도구 → **프로페셔널 계정으로 전환**(비즈니스)
2. 페이스북 페이지를 만들고 인스타 계정과 연결
3. developers.facebook.com 에서 앱 생성 → Instagram Graph API 추가 → `instagram_content_publish` 권한으로 **장기 액세스 토큰** 발급
4. `IG_USER_ID`, `IG_ACCESS_TOKEN` 를 Secrets에 등록
5. 업로드: Actions → "인스타 업로드 (수동 승인)" → Run workflow (GitHub 모바일 앱에서도 가능)

## 매일 할 일 (2분)
1. 작업실 페이지에서 오늘 날짜 클릭
2. **제목 복사 → 본문 복사** → 네이버 블로그에 붙여넣기 → 발행
3. 카드뉴스 확인 후 인스타 업로드 버튼 (또는 자동)

## 로컬에서 테스트
```bash
pip install -r requirements.txt
python -m src.main --sample   # 샘플 데이터, API 키 없이 동작 확인
```

## 구조
```
src/sources/alio.py     잡알리오 API 수집
src/sources/saramin.py  사람인 API 수집 (검색어 목록 수정 가능)
src/classify.py         Claude 분류·요약 (프롬프트 수정 가능)
src/render.py           카드뉴스 이미지
src/site.py             블로그 글·캡션·작업실 페이지
src/instagram.py        인스타 업로드
data/seen.json          이미 올린 공고 기록 (중복 방지)
docs/                   작업실 페이지 (GitHub Pages)
```

## 다음 단계 아이디어
- 교육청 기간제 보건교사 게시판, 나라일터(공무원), 고용24 수집 추가
- 마감 임박 공고 주간 정리
- 공고별 개별 블로그 글 (검색 유입 강화)

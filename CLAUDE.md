# 탈임상 간호사 공고 — 일일 분류 작업 안내 (Claude용)

GitHub Actions가 매일 06:47(KST)에 공고를 수집해 `data/inbox/YYYY-MM-DD.json` 으로 커밋한다.
예약된 Claude Code 세션이 이 파일을 분류하고 콘텐츠를 만들어 push 한다. **Claude API는 쓰지 않는다** (네가 직접 분류).

## 매일 할 일
1. `git pull origin main`
2. `ls data/inbox/` — 파일이 없으면 "오늘 새 공고 없음"이라고 보고하고 끝.
3. 파일마다(오래된 날짜부터) 각 공고 객체에 아래 필드를 채워 **같은 파일에 저장**:
   - `is_target` (bool): 간호사 면허 소지자가 지원 가능한 **탈임상(병원 밖·비임상)** 공고면 true
     - 병동/외래/수술실/응급실/중환자실/요양병원 등 환자 직접 간호 = false
     - 병원 소속이어도 보험심사·QI·연구간호사·CRC처럼 비임상 = true
     - 간호사와 무관(일반사무, 의사·약사 전용 등) = false
   - `category`: `"공공"`(공기업·공무원·보건소·군무원) / `"학교"`(보건교사) / `"기업"`(산업간호사·제약·보험심사·헬스케어) / `"연구"`(CRC·CRA·연구간호사·연구기관). is_target=false면 `null`
   - `job_role`: 짧은 직무명 (예: 산업간호사, CRC, 요양직, 보건교사, 보험심사) — 14자 이내
   - `summary`: 지원자 관점 2~3문장 한국어 요약 (카드에 5줄까지 들어감, 120자 안팎)
   - `requirements`: 핵심 자격요건 최대 3개, 각각 짧게 (예: "간호사 면허", "임상경력 2년 이상")
   - `tags`: 해시태그용 단어 최대 4개 (# 없이, 공백 없이)
   - **원문(`raw_text`, `title`)에 없는 정보는 절대 지어내지 말 것** (연봉, 마감일, 경력 등)
   - 공고가 많으면 Python 스크립트로 JSON을 읽고 쓰되, 판단 자체는 네가 직접 한다.
4. `python -m src.main check YYYY-MM-DD` → `OK` 나올 때까지 수정
5. 폰트 확인: `fc-list | grep -q NotoSansCJK || (apt-get update -q && apt-get install -y -q fonts-noto-cjk)`
   그리고 `pip install -q -r requirements.txt`
6. `python -m src.main build YYYY-MM-DD` (inbox 파일은 `data/jobs/`로 자동 이동)
7. 카드 1~2장을 열어 글자 넘침이 없는지 눈으로 확인 (`docs/YYYY-MM-DD/card-01.jpg`)
8. 커밋 & 푸시:
   `git add -A data docs && git commit -m "분류·콘텐츠 생성 YYYY-MM-DD" && git push origin main`
   (push가 네트워크 오류로 실패하면 2·4·8·16초 간격으로 재시도)
9. 결과를 한 줄로 보고: 전체 N건 중 탈임상 M건 (카테고리별 개수), 작업실 페이지 주소
   https://a55796196-sudo.github.io/nurse_jobs/YYYY-MM-DD/

## 주의
- 이 환경에서는 국내 채용 사이트에 직접 접속이 안 된다. 수집은 GitHub Actions 담당이므로 직접 수집하려 하지 말 것.
- `data/seen.json`, `src/` 코드는 사용자가 요청하지 않는 한 수정하지 않는다.

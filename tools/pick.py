"""일회성: 수도권 간호 관련 진행 중 공고 후보 + 상세(첨부/사이트) 확인."""
import json, os, re, sys, requests
KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
def api(path, **p):
    p.update(serviceKey=KEY, resultType="json")
    for base in ("https://apis.data.go.kr", "http://apis.data.go.kr") * 2:
        try:
            return requests.get(f"{base}/1051000/recruitment/{path}", params=p, timeout=60).json()
        except Exception as e:
            print("재시도", e.__class__.__name__)
    return {}
items = []
for page in range(1, 8):
    res = api("list", pageNo=page, numOfRows=100, ongoingYn="Y").get("result") or []
    items += res
    if len(res) < 100: break
NURSE = re.compile(r"간호|보건관리|임상시험|연구간호|CRC|코디네이터")
CLIN = re.compile(r"병동|수술실|중환자|응급실|3교대|교대근무|외래|NICU|분만실|조무사")
for it in items:
    blob = " ".join(str(it.get(k) or "") for k in ("recrutPbancTtl", "aplyQlfcCn", "prefCondCn"))
    if not NURSE.search(blob) or not re.search("서울|경기|인천", it.get("workRgnNmLst") or ""):
        continue
    print(f"\n#### [{'임상의심' if CLIN.search(blob) else '후보'}] {it['instNm']} | {it['recrutPbancTtl']} | {it.get('hireTypeNmLst')} | {it.get('workRgnNmLst')} | ~{it.get('pbancEndYmd')} | 인원 {it.get('recrutNope')} | sn {it['recrutPblntSn']} | {it.get('srcUrl')}")
    print("자격:", " ".join((it.get("aplyQlfcCn") or "").split())[:900])

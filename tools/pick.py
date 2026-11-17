"""일회성: 병원 제외, 공단·공기업 진행 중 공고 중 간호사 지원 가능(면허 자격/우대)한 것."""
import os, re, requests
KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
def api(path, **p):
    p.update(serviceKey=KEY, resultType="json")
    for base in ("https://apis.data.go.kr", "http://apis.data.go.kr") * 3:
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
print("진행 중 전체", len(items))
HOSP = re.compile(r"병원|의료원|의학원|암센터|치과|적십자")
for it in items:
    blob = " ".join(str(it.get(k) or "") for k in ("recrutPbancTtl", "aplyQlfcCn", "prefCondCn", "prefCn", "scrnprcdrMthdExpln"))
    if HOSP.search(it["instNm"]) or not re.search(r"간호", blob):
        continue
    i = blob.find("간호")
    print(f"\n#### {it['instNm']} | {it['recrutPbancTtl']} | {it.get('hireTypeNmLst')} | {it.get('recrutSeNm')} | {it.get('workRgnNmLst')} | {it.get('pbancBgngYmd')}~{it.get('pbancEndYmd')} | 인원 {it.get('recrutNope')} | sn {it['recrutPblntSn']} | {it.get('srcUrl')}")
    print("간호 주변:", " ".join(blob[max(0, i - 300): i + 400].split()))

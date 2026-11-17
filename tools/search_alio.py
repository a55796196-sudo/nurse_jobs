"""잡알리오 진행 중 공고에서 키워드 검색 (일회성)."""
import os, re, sys, requests
KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
PAT = re.compile(sys.argv[1] if len(sys.argv) > 1 else "의료기기|인허가|RA|식품의약|식약|보건산업진흥|임상시험", re.I)
items = []
for page in range(1, 8):
    r = requests.get("https://apis.data.go.kr/1051000/recruitment/list",
                     params={"serviceKey": KEY, "resultType": "json", "pageNo": page, "numOfRows": 100, "ongoingYn": "Y"}, timeout=60).json()
    res = r.get("result") or []
    items += res
    if len(res) < 100:
        break
print("진행 중 전체", len(items))
for it in items:
    blob = " ".join(str(it.get(k) or "") for k in ("instNm", "recrutPbancTtl", "ncsCdNmLst", "aplyQlfcCn", "prefCondCn"))
    if PAT.search(blob):
        print("\n####", it["instNm"], "|", it["recrutPbancTtl"], "|", it.get("hireTypeNmLst"), "|", it.get("recrutSeNm"),
              "|", it.get("pbancBgngYmd"), "~", it.get("pbancEndYmd"), "| 인원", it.get("recrutNope"), "| sn", it["recrutPblntSn"], "|", it.get("srcUrl"))
        print("NCS:", it.get("ncsCdNmLst"), "| 학력:", it.get("acbgCondNmLst"), "| 지역:", it.get("workRgnNmLst"))
        print("자격:", " ".join((it.get("aplyQlfcCn") or "").split())[:1200])
        print("우대:", " ".join((it.get("prefCn") or "").split())[:400])
        print("전형:", " ".join((it.get("scrnprcdrMthdExpln") or "").split())[:400])

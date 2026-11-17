"""일회성: 한국보건의료정보원 제6차 상세."""
import os, requests
KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
det = {}
for base in ("https://apis.data.go.kr", "http://apis.data.go.kr") * 3:
    try:
        det = requests.get(base + "/1051000/recruitment/detail", params={"serviceKey": KEY, "resultType": "json", "sn": 306965}, timeout=60).json().get("result") or {}
        break
    except Exception as e:
        print("재시도", e.__class__.__name__)
for k in ("recrutPbancTtl", "hireTypeNmLst", "workRgnNmLst", "acbgCondNmLst", "recrutNope", "pbancBgngYmd", "pbancEndYmd", "srcUrl"):
    print(k, ":", det.get(k))
print("첨부:", [f.get("atchFileNm") for f in det.get("files") or []])
print("모집단계:", [(s.get("recrutPbancTtl"), s.get("recrutNope")) for s in det.get("steps") or []][:40])
for k in ("aplyQlfcCn", "prefCn", "scrnprcdrMthdExpln"):
    print("\n" + k, ":", " ".join(str(det.get(k) or "").split())[:4000])

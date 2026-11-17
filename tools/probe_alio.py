"""잡알리오 API 응답 구조 확인용 (디버그). 공고 1건의 목록 항목 전체와 상세 API 후보 응답을 출력."""
import json
import os

import requests

KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
BASE = "https://apis.data.go.kr/1051000/recruitment"


def get(path, **params):
    params.update(serviceKey=KEY, resultType="json")
    try:
        r = requests.get(f"{BASE}/{path}", params=params, timeout=60)
        print(f"\n=== {path} {params.get('sn', '')} -> HTTP {r.status_code}")
        print(r.text[:4000])
        return r
    except requests.RequestException as e:
        print(f"\n=== {path} 실패: {e}")


r = get("list", pageNo=1, numOfRows=30, ongoingYn="Y")
items = (r.json().get("result") or []) if r is not None and r.status_code == 200 else []
nurse = [i for i in items if "간호" in json.dumps(i, ensure_ascii=False)]
it = (nurse or items or [{}])[0]
print("\n=== 목록 항목 전체 키:", sorted(it.keys()))
print(json.dumps(it, ensure_ascii=False, indent=1)[:6000])
sn = it.get("recrutPblntSn")
for path in ("detail", "view", "info"):
    get(path, sn=sn)

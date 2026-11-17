"""잡알리오 첨부파일 다운로드 재시도 (디버그): 사이트 방문 후 같은 세션으로 내려받기."""
import os
import re
import subprocess
import tempfile

import requests

KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
det = requests.get("https://apis.data.go.kr/1051000/recruitment/detail",
                   params={"serviceKey": KEY, "resultType": "json", "sn": 307082}, timeout=60).json()["result"]
f = det["files"][0]
print("파일:", f["atchFileNm"])

s = requests.Session()
for warm in ("https://opendata.alio.go.kr/", f"https://job.alio.go.kr/recruitview.do?idx={det['recrutPblntSn']}"):
    r = s.get(warm, timeout=60)
    print("방문", warm, r.status_code, len(r.content))
    if "job.alio" in warm:
        print("공고 페이지 다운로드 링크 후보:", sorted(set(re.findall(r"[\"'](/?[^\"' ]*(?:down|Down|file|File)[^\"' ]*)[\"']", r.text)))[:15])
r = s.get(f"https://www.alio.go.kr/download/download.json?fileNo={f['recrutAtchFileNo']}", timeout=60)
print("다운로드:", r.status_code, r.headers.get("content-type"), r.headers.get("content-disposition"), len(r.content), r.content[:8])
if r.content[:4] == b"\xd0\xcf\x11\xe0":
    with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as t:
        t.write(r.content)
    out = subprocess.run(["hwp5txt", t.name], capture_output=True, text=True)
    print("추출:", len(out.stdout), out.stderr[:300])
    print(" ".join(out.stdout.split())[:3000])

"""잡알리오 첨부파일(공고문) 다운로드·텍스트 추출 가능 여부 확인 (디버그)."""
import io
import json
import os
import subprocess
import tempfile
import zipfile

import requests

KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
BASE = "https://apis.data.go.kr/1051000/recruitment"


def api(path, **params):
    params.update(serviceKey=KEY, resultType="json")
    return requests.get(f"{BASE}/{path}", params=params, timeout=60).json()


items = []
for page in (1, 2, 3):
    items += api("list", pageNo=page, numOfRows=100, ongoingYn="Y").get("result") or []
nurse = [i for i in items if "간호" in (i.get("recrutPbancTtl", "") + i.get("aplyQlfcCn", ""))]
print("간호 공고", len(nurse), "/ 전체", len(items))
with_files = []
for i in nurse[:15]:
    det = api("detail", sn=i["recrutPblntSn"]).get("result") or {}
    print("detail", i["recrutPblntSn"], "files:", len(det.get("files") or []), "steps:", len(det.get("steps") or []))
    if det.get("files"):
        with_files.append(det)
print("첨부 있는 공고", len(with_files))
for it in with_files[:1]:
    print("\n=== 공고", it["recrutPblntSn"], it["instNm"], it["recrutPbancTtl"])
    print("files:", json.dumps(it["files"], ensure_ascii=False, indent=1)[:2500])
    print("steps:", json.dumps(it.get("steps"), ensure_ascii=False)[:800])
    for f in it["files"][:3]:
        url = next((v for k, v in f.items() if isinstance(v, str) and v.startswith("http")), None)
        print("\n--- 파일", f, "\nURL:", url)
        if not url:
            continue
        try:
            r = requests.get(url, timeout=60)
        except requests.RequestException as e:
            print("다운로드 실패:", e)
            continue
        print("HTTP", r.status_code, r.headers.get("content-type"), r.headers.get("content-disposition"), len(r.content), "bytes")
        if "html" in (r.headers.get("content-type") or ""):
            import re
            body = r.text
            print("HTML 제목:", re.findall(r"<title>(.*?)</title>", body, re.S)[:1])
            print("HTML 본문 텍스트:", " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\\1>", " ", body, flags=re.S)).split())[:800])
            print("script/링크 일부:", re.findall(r"(location[^;]{0,200}|action=\"[^\"]+\"|href=\"[^\"]*down[^\"]*\")", body)[:10])
            break
        head = r.content[:8]
        with tempfile.NamedTemporaryFile(delete=False) as t:
            t.write(r.content)
        text = ""
        if head.startswith(b"%PDF"):
            text = subprocess.run(["pdftotext", "-layout", t.name, "-"], capture_output=True, text=True).stdout
        elif head.startswith(b"PK"):
            z = zipfile.ZipFile(io.BytesIO(r.content))
            names = z.namelist()
            print("zip 내용:", names[:15])
            secs = [n for n in names if n.startswith("Contents/section")]
            import re
            text = " ".join(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf8", "ignore")) for n in secs)
        elif head.startswith(b"\xd0\xcf\x11\xe0"):
            text = subprocess.run(["hwp5txt", t.name], capture_output=True, text=True).stdout
        print("추출 글자 수:", len(text))
        print(" ".join(text.split())[:3000])

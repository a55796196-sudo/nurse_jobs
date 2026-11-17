"""알리오 경영공시 '직원 평균보수'(신입사원 초임 포함) 페이지 접근·파싱 가능 여부 확인 (디버그)."""
import re

import requests

for inst in ("C0179", "C0331"):
    url = f"https://www.alio.go.kr/item/itemReportTerm.do?apbaId={inst}&reportFormRootNo=2060"
    try:
        r = requests.get(url, timeout=60)
    except requests.RequestException as e:
        print(inst, "실패", e)
        continue
    text = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", " ", r.text, flags=re.S)).split())
    print(f"\n=== {inst} HTTP {r.status_code} {len(r.text)}자")
    i = text.find("초임")
    print("초임 주변:", text[max(0, i - 300): i + 1200] if i >= 0 else "(초임 없음)", "\n")
    print("앞부분:", text[:600])
    print("iframe/ajax 후보:", sorted(set(re.findall(r"[\"'](/[^\"' ]*(?:report|Report|item)[^\"' ]*\.(?:do|json))", r.text)))[:20])

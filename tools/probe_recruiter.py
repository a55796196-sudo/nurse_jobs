"""기관 채용 사이트(recruiter.co.kr) 공고 페이지에서 근무조건을 읽을 수 있는지 확인 (디버그)."""
import re

import requests

url = "https://nhimc.recruiter.co.kr/career/jobs/121616"
r = requests.get(url, timeout=60)
html = r.text
text = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.S)).split())
print("HTTP", r.status_code, len(html), "자 / 본문 텍스트", len(text), "자")
for kw in ("보수", "만원", "근무시간", "복리후생"):
    i = text.find(kw)
    print(f"[{kw}]", text[max(0, i - 150): i + 300] if i >= 0 else "없음")
print("이미지:", re.findall(r"<img[^>]+src=\"([^\"]+)\"", html)[:10])
print("API 후보:", sorted(set(re.findall(r"[\"'](/[^\"' ]*(?:api|json|jobs)[^\"' ]*)[\"']", html)))[:20])
print("앞부분:", text[:500])

"""일회성: 지정한 잡알리오 공고 + 교육청 공고를 Job 형태로 받아 inbox 에 추가."""
import json, os, re, requests
from pathlib import Path
from src.models import Job
from src.main import INBOX, read_jobs, write_jobs, load_seen, save_seen, today_kst
from src.sources.alio import _fmt_date

KEY = (os.environ.get("DATA_GO_KR_KEY") or "").strip()
SNS = [306965, 306789, 307013]
SEN = ["https://work.sen.go.kr/work/search/recInfo/BD_selectRecDetail.do?q_rcrtSn=110792"]

def api(**p):
    p.update(serviceKey=KEY, resultType="json")
    for base in ("https://apis.data.go.kr", "http://apis.data.go.kr") * 3:
        try:
            return requests.get(base + "/1051000/recruitment/detail", params=p, timeout=60).json().get("result") or {}
        except Exception as e:
            print("재시도", e.__class__.__name__)
    return {}

jobs = []
for sn in SNS:
    it = api(sn=sn)
    text = " ".join(str(it.get(k) or "") for k in ("recrutPbancTtl", "ncsCdNmLst", "aplyQlfcCn", "prefCondCn", "recrutSeNm"))
    j = Job(source="alio", source_id=str(sn), title=it.get("recrutPbancTtl", "").strip(), org=it.get("instNm", "").strip(),
            url=it.get("srcUrl") or "", deadline=_fmt_date(it.get("pbancEndYmd")), location=it.get("workRgnNmLst"),
            employment_type=it.get("hireTypeNmLst"), raw_text=text[:3000], start_date=_fmt_date(it.get("pbancBgngYmd")),
            extra={k: str(v)[:4000] for k, v in it.items() if v not in (None, "", []) and k not in ("files", "steps")})
    j.extra["files"] = [f.get("atchFileNm") for f in it.get("files") or []]
    j.extra["steps"] = sorted({s.get("recrutPbancTtl") for s in it.get("steps") or [] if s.get("recrutPbancTtl")})
    j.extra["alio_url"] = f"https://job.alio.go.kr/recruitview.do?idx={sn}"
    jobs.append(j); print("ALIO", sn, j.org, j.title)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for url in SEN:
        pg.goto(url, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2500)
        texts = []
        for fr in pg.frames:
            try: texts.append(" ".join(fr.inner_text("body", timeout=10000).split()))
            except Exception: pass
        body = "\n".join(texts)
        m = re.search(r"^.*?\s(\S+학교)\s+(.+?)\s+관심공고", body)
        title = m.group(2) if m else "보건 대체(시간)강사 채용"
        org = m.group(1) if m else "학교"
        dl = re.search(r"접수기간\s*\S+\s*\S+\s*~\s*(\d{4})\.(\d{2})\.(\d{2})", body)
        j = Job(source="sen", source_id=re.search(r"q_rcrtSn=(\d+)", url).group(1), title=title, org=org, url=url,
                deadline=f"{dl.group(1)}-{dl.group(2)}-{dl.group(3)}" if dl else None, location="서울",
                employment_type="계약제교원(시간강사)", raw_text=body[:3000], extra={"site_text": body[:8000], "detail_url": url})
        jobs.append(j); print("SEN", j.org, j.title, j.deadline)
    b.close()

f = INBOX / f"{today_kst()}.json"
existing = read_jobs(f) if f.exists() else []
keys = {j.key for j in existing}
existing += [j for j in jobs if j.key not in keys]
write_jobs(f, existing)
seen = load_seen()
for j in jobs: seen[j.key] = today_kst()
save_seen(seen, today_kst())
print("저장", f, len(existing))

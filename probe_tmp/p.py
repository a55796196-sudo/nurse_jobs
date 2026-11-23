from src.sources import work24
for j in work24.fetch():
    print("JOB", j.extra.get("kw") if j.extra else "", "|", j.org, "|", j.title[:70], "|", j.deadline, "|", "간호" in (j.raw_text or "") + str(j.extra.get("origin_text","")))

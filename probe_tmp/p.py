from src.sources import work24
for j in work24.fetch(days=4, max_detail=6):
    print("JOB", j.key, "|", j.org, "|", j.title[:40], "|", j.employment_type, "|", j.url)
    if j.extra.get("origin_text"): print("   O", j.extra["origin_text"][:500])

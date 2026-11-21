from src.sources import work24
js = work24.fetch(days=7, max_detail=2)
for j in js:
    print("JOB", j.key, "|", j.org, "|", j.title, "|", j.location, "|", j.deadline, "|", j.extra["search_kw"])

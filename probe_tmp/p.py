from src.sources import work24, konect
for j in work24.fetch(days=7, max_detail=3):
    print("JOB", j.key, "|", j.org, "|", j.title, "|", j.location, "|", j.start_date, "~", j.deadline, "|", j.extra["search_kw"])
    print("   L", j.extra["list_text"][:300])
    if j.extra["site_text"]: print("   D", j.extra["site_text"][:600])
print("KONECT", [(j.title, j.deadline) for j in konect.fetch(days=120)])

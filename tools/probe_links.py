from src.sources import konect
for j in konect.fetch(days=120):
    print("JOB", j.key, "|", j.org, "|", j.title, "|", j.start_date, "~", j.deadline)
    print("   ", (j.extra.get("site_text") or "")[:500])

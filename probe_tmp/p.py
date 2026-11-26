from src.sources import nursevillage, kaohn
for mod in (kaohn, nursevillage):
    for j in mod.fetch():
        print("JOB", j.source, j.org, "|", j.title[:60], "|", j.deadline, j.extra.get("deadline_time"), "|", j.location, "|", j.employment_type, "|", (j.url or "")[:70])
        print("   TXT", j.extra["site_text"][:400])

from src.sources import incruit
for j in incruit.fetch():
    print("JOB", j.org, "|", j.title[:60], "|", j.deadline, "|", j.employment_type, "|", j.location, "| AI" if j.extra["ai_article"] else "", "| 간호" if "간호" in j.raw_text else "")
    print("CONT", len(j.extra["origin_text"]), j.extra["origin_text"][:250])

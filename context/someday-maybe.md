# Someday / Maybe

Ideas worth revisiting when the time is right. Not committed, not forgotten.

---

## Mnemosyne: migrate CSV to SQLite

**What:** Replace `context/portfolio/project-database.csv` with a local SQLite database at the same path (or nearby).

**Why:** Long-text fields (Testimonials, Lessons, Project Description) are awkward in CSV and will cause quoting bugs as data fills in. SQLite gives proper column types, no escaping headaches, and stays local/git-trackable.

**When:** When the CSV starts to feel painful — quoting errors, multi-line fields breaking skills, or data volume growing past ~200 projects.

**Note:** Keep the local-first pattern regardless. WordPress is a publish target (via `mnemosyne_sync.py`), not the source of truth.

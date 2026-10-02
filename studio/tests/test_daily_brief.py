import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "collectors"))

import daily_brief as b

TODAY = dt.date(2026, 9, 17)

MIRROR = """# Bot Asana Task Mirror

## Test

### TST-001 — Overdue thing
- **Local ID:** TST-001
- **Section:** TO DO
- **Looper Status:** none
- **Due:** 2026-08-01 **(OVERDUE)**
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** none
- **Modified:** 2026-09-10T10:00:00
- **URL:** https://app.asana.com/x/1

### TST-002 — Blocked thing
- **Local ID:** TST-002
- **Section:** DOING
- **Looper Status:** Blocked
- **Due:** none
- **Notes:** No notes.
- **Blockers:** 2026-08-20 — Which repo?
- **Progress:** Blocked
- **Modified:** 2026-08-20T10:00:00
- **URL:** https://app.asana.com/x/2

### TST-003 — Issue invoice
- **Local ID:** TST-003
- **Section:** TO DO
- **Looper Status:** none
- **Due:** 2026-09-20
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** none
- **Modified:** 2026-09-01T10:00:00
- **URL:** https://app.asana.com/x/3

### TST-004 — Chase client for content
- **Local ID:** TST-004
- **Section:** TO DO
- **Looper Status:** none
- **Due:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** none
- **Modified:** 2026-07-01T10:00:00
- **URL:** https://app.asana.com/x/4

### TST-005 — Finished work
- **Local ID:** TST-005
- **Section:** DOING
- **Looper Status:** Review
- **Due:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Ready for review 2026-09-01. Done.
- **Modified:** 2026-09-01T10:00:00
- **URL:** https://app.asana.com/x/5

## DONE

### TST-006 — Old overdue but done
- **Local ID:** TST-006
- **Section:** DONE
- **Due:** 2026-01-01 **(OVERDUE)**
- **Modified:** 2026-01-01T10:00:00
"""


def _projects(tasks):
    return {"TST": {"status": "active", "root": Path("/nonexistent"), "tasks": tasks}}


def test_parse_mirror_skips_done_and_strips_overdue_marker():
    tasks = b.parse_mirror(MIRROR)
    assert [t["lid"] for t in tasks] == ["TST-001", "TST-002", "TST-003", "TST-004", "TST-005"]
    assert tasks[0]["due"] == "2026-08-01"


def test_check_tasks_classifies_each_kind_once():
    found = {f["key"]: f for f in b.check_tasks(_projects(b.parse_mirror(MIRROR)), TODAY)}
    assert found["task:TST-001:overdue"]["detail"].startswith("47 day(s) overdue")
    assert found["task:TST-001:overdue"]["severity"] == "high"
    assert found["task:TST-002:blocked"]["age_days"] == 28
    # TST-003 is an invoice due in 3 days: on schedule, so not a finding at all
    assert not any(k.startswith("task:TST-003:") for k in found)
    assert found["task:TST-004:client"]["area"] == "Clients"
    assert found["task:TST-005:review"]["age_days"] == 16
    assert not any("TST-006" in k for k in found)


def test_many_overdue_tasks_roll_up_and_leave_today():
    task = b.parse_mirror(MIRROR)[0]
    tasks = [dict(task, lid=f"TST-{i:03d}") for i in range(10, 17)]
    found = b.check_tasks(_projects(tasks), TODAY)
    pile = [f for f in found if f["key"] == "project:TST:overdue-pile"]
    assert len(pile) == 1 and pile[0]["severity"] == "high"
    singles = [f for f in found if f["key"].endswith(":overdue")]
    assert all(f["severity"] == "normal" and f["today"] is False for f in singles)
    _, _, top = b.render(found, TODAY)
    assert [f["key"] for f in top] == ["project:TST:overdue-pile"]


def test_untouched_task_is_flagged_when_nothing_else_would():
    base = b.parse_mirror(MIRROR)[2]
    task = dict(base, lid="TST-010", name="Tidy the footer", due="none",
                modified="2026-06-01T10:00:00")
    found = {f["key"]: f for f in b.check_tasks(_projects([task]), TODAY)}
    f = found["task:TST-010:untouched"]
    assert f["severity"] == "normal" and f["age_days"] == 108
    assert "untouched for 108 days" in f["detail"]


def test_many_untouched_tasks_roll_up():
    base = b.parse_mirror(MIRROR)[2]
    tasks = [dict(base, lid=f"TST-{i:03d}", name="Tidy the footer", due="none",
                  modified="2026-06-01T10:00:00") for i in range(20, 27)]
    found = b.check_tasks(_projects(tasks), TODAY)
    pile = [f for f in found if f["key"] == "project:TST:untouched-pile"]
    assert len(pile) == 1
    singles = [f for f in found if f["key"].endswith(":untouched")]
    assert len(singles) == 7 and all(f["today"] is False for f in singles)


def test_first_seen_never_changes_severity_and_prunes_resolved():
    fs = [b.finding("a", "Finance", "normal", "A"), b.finding("c", "Finance", "critical", "C")]
    state = {"a": "2026-09-01", "gone": "2026-08-01"}
    new_state = b.stamp_first_seen(fs, state, TODAY)
    # sitting on the list for 16 days must not promote anything
    assert fs[0]["severity"] == "normal" and fs[0]["raised_days"] == 16
    assert fs[1]["severity"] == "critical" and fs[1]["raised_days"] == 0
    assert new_state == {"a": "2026-09-01", "c": "2026-09-17"}


def test_a_job_failing_now_outranks_older_rot():
    failing = b.finding("f", "Operations", "high", "F", acute=True)        # age 0
    ancient = b.finding("a", "Projects", "high", "A", age_days=476)
    failing["raised_days"] = ancient["raised_days"] = 0
    assert [f["key"] for f in sorted([ancient, failing], key=b.rank)] == ["f", "a"]


def test_acute_does_not_outrank_a_higher_severity():
    failing = b.finding("f", "Operations", "high", "F", acute=True)
    money = b.finding("m", "Finance", "critical", "M")
    failing["raised_days"] = money["raised_days"] = 0
    assert [f["key"] for f in sorted([failing, money], key=b.rank)] == ["m", "f"]


def test_rank_puts_the_older_problem_above_the_older_report():
    worse = b.finding("w", "Projects", "high", "W", age_days=90)
    worse["raised_days"] = 0
    stale_report = b.finding("s", "Projects", "high", "S", age_days=10)
    stale_report["raised_days"] = 60
    assert sorted([stale_report, worse], key=b.rank)[0]["key"] == "w"


def test_untouched_severity_rises_with_the_age_of_the_task():
    base = b.parse_mirror(MIRROR)[2]
    young = dict(base, lid="TST-020", name="Tidy the footer", due="none",
                 modified="2026-06-01T10:00:00")          # 108 days
    ancient = dict(base, lid="TST-021", name="Tidy the footer", due="none",
                   modified="2025-01-01T10:00:00")        # 624 days
    found = {f["key"]: f for f in b.check_tasks(_projects([young, ancient]), TODAY)}
    assert found["task:TST-020:untouched"]["severity"] == "normal"
    assert found["task:TST-021:untouched"]["severity"] == "high"


def test_check_cron_flags_failing_quiet_and_ignores_old_errors(tmp_path):
    ok = tmp_path / "ok.log"
    ok.write_text("Traceback (most recent call last):\nboom\n" + "fine\n" * 10)
    bad = tmp_path / "bad.log"
    bad.write_text("run\nTraceback (most recent call last):\nFileNotFoundError: x\n")
    import os
    # daily job (max_age 30h): 5 days silent is several cycles dead
    dead = tmp_path / "dead.log"
    dead.write_text("done\n")
    ts = dt.datetime.now().timestamp() - 5 * 86400
    os.utime(dead, (ts, ts))
    # ...while one missed cycle is merely late
    late = tmp_path / "late.log"
    late.write_text("done\n")
    ts = dt.datetime.now().timestamp() - 2 * 86400
    os.utime(late, (ts, ts))
    crontab = (f"MAILTO=\"\"\n"
               f"0 8 * * * cd {tmp_path} && python3 ok.py >> ok.log 2>&1\n"
               f"0 8 * * * cd {tmp_path} && python3 bad.py >> bad.log 2>&1\n"
               f"0 8 * * * cd {tmp_path} && python3 dead.py >> dead.log 2>&1\n"
               f"0 8 * * * cd {tmp_path} && python3 late.py >> late.log 2>&1\n"
               f"0 8 * * * cd {tmp_path} && python3 missing.py >> missing.log 2>&1\n")
    found = {f["key"]: f for f in b.check_cron(TODAY, crontab_text=crontab)}
    assert "ops:cron:ok.py" not in found
    assert found["ops:cron:bad.py"]["title"].endswith("is failing")
    assert found["ops:cron:dead.py"]["severity"] == "high"
    assert found["ops:cron:dead.py"]["age_days"] == 5
    assert found["ops:cron:late.py"]["severity"] == "normal"
    assert "no log" in found["ops:cron:missing.py"]["title"]


def test_cron_max_age():
    assert b._cron_max_age_hours(["0", "*", "*", "*", "*"]) == 3
    assert b._cron_max_age_hours(["0", "8", "*", "*", "*"]) == 30
    assert b._cron_max_age_hours(["25", "8", "*", "*", "1,4"]) == 4 * 24 + 6
    assert b._cron_max_age_hours(["0", "9", "*", "*", "1"]) == 7 * 24 + 6


def test_obsidian_uri(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path / "Work Notes"))
    uri = b.obsidian_uri(tmp_path / "Work Notes" / "Daily Brief" / "2026-09-17-daily-brief.md")
    assert uri == "obsidian://open?vault=Work%20Notes&file=Daily%20Brief/2026-09-17-daily-brief"


def test_assigned_to_me_matches_only_the_users_gid():
    assert b.assigned_to_me({"assignee": "Mark Bain (507443625075)"}, "507443625075")
    assert not b.assigned_to_me({"assignee": "BainBot (1209202434387214)"}, "507443625075")
    assert not b.assigned_to_me({"assignee": "none"}, "507443625075")
    assert not b.assigned_to_me({"assignee": "Mark Bain (507443625075)"}, "")

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

import ops_status as o

NOW = dt.datetime(2026, 10, 1, 16, 22)  # a Thursday


def test_last_fire_daily_job_earlier_today():
    assert o.last_fire("40 8 * * *", NOW) == dt.datetime(2026, 10, 1, 8, 40)


def test_last_fire_daily_job_not_yet_run_today_is_yesterday():
    assert o.last_fire("0 17 * * *", NOW) == dt.datetime(2026, 9, 30, 17, 0)


def test_last_fire_weekly_monday_job():
    assert o.last_fire("0 9 * * 1", NOW) == dt.datetime(2026, 9, 28, 9, 0)


def test_last_fire_day_of_week_list():
    # Mon and Thu: Thursday 08:25 has already passed
    assert o.last_fire("25 8 * * 1,4", NOW) == dt.datetime(2026, 10, 1, 8, 25)


def test_last_fire_hour_list_and_hourly():
    assert o.last_fire("0 9,17 * * *", NOW) == dt.datetime(2026, 10, 1, 9, 0)
    assert o.last_fire("0 * * * *", NOW) == dt.datetime(2026, 10, 1, 16, 0)


def test_last_fire_sunday_as_zero_and_seven():
    sunday = dt.datetime(2026, 9, 27, 6, 0)
    assert o.last_fire("0 6 * * 0", NOW) == sunday
    assert o.last_fire("0 6 * * 7", NOW) == sunday


def test_job_name_and_log_path():
    cmd = ("cd /home/bain/ops/bain-studio && python3 studio/collectors/daily_brief.py "
           ">> studio/collectors/daily_brief.log 2>&1")
    assert o._name(cmd) == "daily_brief"
    assert o._log_path(cmd) == Path("/home/bain/ops/bain-studio/studio/collectors/daily_brief.log")


def test_upwork_jobs_are_namespaced():
    cmd = "cd /home/bain/ops/upwork-proposals && .venv/bin/python pipeline/run.py >> pipeline/run.log 2>&1"
    assert o._name(cmd) == "upwork/run"

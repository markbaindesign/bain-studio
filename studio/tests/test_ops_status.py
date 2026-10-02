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


def test_parse_tailscale_orders_online_first_then_most_recently_seen():
    import json
    raw = json.dumps({
        "BackendState": "Running",
        "Self": {"HostName": "me", "TailscaleIPs": ["100.1.1.1"], "OS": "linux", "Online": True},
        "Peer": {
            "a": {"HostName": "old", "TailscaleIPs": ["100.1.1.2"], "Online": False, "LastSeen": "2026-01-01T00:00:00Z"},
            "b": {"HostName": "recent", "TailscaleIPs": ["100.1.1.3"], "Online": False, "LastSeen": "2026-09-30T00:00:00Z"},
            "c": {"HostName": "live", "TailscaleIPs": ["100.1.1.4"], "Online": True, "LastSeen": "2026-01-01T00:00:00Z"},
        },
    })
    out = o.parse_tailscale(raw)
    assert out["state"] == "Running" and out["self"]["ip"] == "100.1.1.1"
    assert [p["name"] for p in out["peers"]] == ["live", "recent", "old"]


def test_parse_tailscale_handles_no_peers():
    assert o.parse_tailscale('{"BackendState": "Stopped", "Self": {}}')["peers"] == []

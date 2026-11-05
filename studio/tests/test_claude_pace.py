import time
from datetime import datetime

from studio import claude_pace as p


def at(text):
    """A local wall-clock time as a timestamp: '2026-11-05 14:00'."""
    return time.mktime(datetime.strptime(text, "%Y-%m-%d %H:%M").timetuple())


# 2026-11-09 is a Monday, so a weekly window resetting then opened on Monday
# 2026-11-02.
RESET_MON = at("2026-11-09 09:00")


# --- the weekly budget ----------------------------------------------------

def test_a_fresh_week_has_budgeted_nothing():
    pace = p.weekly_pace(RESET_MON, 0, now=at("2026-11-02 09:00"))
    assert pace["expected"] == 0


def test_a_whole_work_day_budgets_twenty_points():
    pace = p.weekly_pace(RESET_MON, 0, now=at("2026-11-03 09:00"))
    assert round(pace["expected"]) == 20


# A window resetting Thursday opened the Thursday before, so by the weekend
# only two work days have been budgeted - far enough from the 100% cap for a
# weekend to show up if it counted.
RESET_THU = at("2026-11-12 09:00")


def test_the_weekend_budgets_nothing():
    # Saturday and Sunday are not work days, so a quiet weekend must not make
    # the following Monday look frugal.
    saturday = p.weekly_pace(RESET_THU, 0, now=at("2026-11-07 12:00"))
    sunday = p.weekly_pace(RESET_THU, 0, now=at("2026-11-08 12:00"))
    assert round(saturday["expected"]) == 40
    assert saturday["expected"] == sunday["expected"]


def test_a_day_is_counted_from_the_hour_the_window_opened():
    # Days are whole 24-hour chunks from the reset time, not calendar days,
    # and each chunk is classified by the day it starts on. Inherited from the
    # JavaScript this came from, and worth knowing: a window that opened at
    # 09:00 on Friday counts Saturday morning as Friday.
    # The window opened Thursday 09:00, so its first day closes at Friday
    # 09:00: an hour before that, Thursday is still 23/24 spent.
    before = p.weekly_pace(RESET_THU, 0, now=at("2026-11-06 08:00"))
    after = p.weekly_pace(RESET_THU, 0, now=at("2026-11-06 10:00"))
    assert round(before["expected"]) == 19
    assert round(after["expected"]) == 21


def test_the_budget_never_exceeds_a_hundred():
    pace = p.weekly_pace(RESET_MON, 50, now=at("2026-11-08 12:00"))
    assert pace["expected"] <= 100


def test_half_a_work_day_budgets_half_of_it():
    pace = p.weekly_pace(RESET_MON, 0, now=at("2026-11-02 21:00"))
    assert 9 < pace["expected"] < 11


# --- the five-hour budget -------------------------------------------------

def test_an_hour_into_the_window_budgets_twenty_points():
    now = time.time()
    pace = p.window_pace(now + 4 * 3600, 0, now=now)
    assert round(pace["expected"]) == 20


def test_a_window_just_opened_has_budgeted_nothing():
    now = time.time()
    assert p.window_pace(now + 5 * 3600, 0, now=now)["expected"] == 0


def test_a_window_about_to_reset_has_budgeted_everything():
    now = time.time()
    assert round(p.window_pace(now + 1, 0, now=now)["expected"]) == 100


# --- the verdict ----------------------------------------------------------

def test_the_thresholds_are_five_and_fifteen_points():
    assert p.state_for(5) == p.OK
    assert p.state_for(5.1) == p.SLIGHTLY_FAST
    assert p.state_for(15) == p.SLIGHTLY_FAST
    assert p.state_for(15.1) == p.FAST


def test_under_budget_is_ok():
    assert p.state_for(-40) == p.OK


def test_a_nearly_spent_window_is_fast_however_well_paced_it_is():
    # The dashboard's own rule reports green at 95% on a Friday, because
    # spending the last of the week on the last day is exactly on budget.
    on_budget = {"expected": 95.0, "over": 0.0, "state": p.OK}
    assert p.colour_state(95, on_budget) == p.FAST
    assert p.colour_state(89, on_budget) == p.OK


def test_pace_for_returns_nothing_without_a_reset_time():
    # No reset means the window's start is unknown, so there is no budget to
    # compare with and nothing honest to draw.
    assert p.pace_for(50, 0, weekly=True) is None
    assert p.pace_for(50, None) is None


def test_pace_for_carries_the_colour_state():
    now = time.time()
    pace = p.pace_for(95, now + 3600, weekly=False, now=now)
    assert pace["colour_state"] == p.FAST

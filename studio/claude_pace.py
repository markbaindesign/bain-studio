"""Is a Claude account's quota burning faster than it should be?

A percentage on its own does not say whether to worry: 60% of the weekly
window is fine on a Thursday and alarming on a Monday morning. These two
functions turn a figure into a verdict by comparing it with what the budget
says should have been spent by now.

    weekly   20% a work day, Monday to Friday; weekends budget nothing
    5-hour   20% an hour, linear from the moment the window opened

Over budget by more than 5 points is `slightly-fast`, by more than 15 is
`fast`, and anything else is `ok`.

The rules were written in JavaScript in the studio dashboard and are now here,
in one place, because the session dash needed them too. `server.py` serves
what this returns and `dashboard.html` renders it, so a change to the budget
happens once.

`colour_state` adds something the dashboard did not have: a window at 90% or
more is `fast` whatever its pace. Pace alone reports green at 95% on a Friday
afternoon, because spending the last of the week's quota on the last day is
exactly on budget - which is the moment the warning is most wanted.
"""

import time

# What a day of work is allowed to spend of the weekly window.
WORKDAY_BUDGET_PCT = 20
# The five-hour window, and what an hour of it is allowed to spend.
FIVE_HOUR_SECONDS = 5 * 3600
WEEK_SECONDS = 7 * 86400

# Points over the budgeted figure before the verdict changes.
SLIGHTLY_FAST_PTS = 5
FAST_PTS = 15

# The level at which the figure speaks for itself, pace or no pace.
LEVEL_FLOOR_PCT = 90

OK = "ok"
SLIGHTLY_FAST = "slightly-fast"
FAST = "fast"


def state_for(over):
    """The verdict for a figure this many points over budget."""
    if over > FAST_PTS:
        return FAST
    if over > SLIGHTLY_FAST_PTS:
        return SLIGHTLY_FAST
    return OK


def weekly_pace(reset_ts, pct, now=None):
    """Where the weekly window should be by now, and whether it is past it.

    The window opened a week before it resets. Every whole work day since
    then budgets 20%, and today budgets the fraction of it that has passed;
    Saturday and Sunday budget nothing, so a weekend does not make Monday
    look frugal.
    """
    now = time.time() if now is None else now
    start = reset_ts - WEEK_SECONDS
    days = 0.0
    day = start
    while day < now:
        end = min(day + 86400, now)
        # 0-4 is Monday to Friday in Python's weekday(); the JavaScript this
        # came from used getDay(), where 1-5 is the same span.
        if time.localtime(day).tm_wday <= 4:
            days += (end - day) / 86400
        day += 86400
    expected = min(100.0, days * WORKDAY_BUDGET_PCT)
    over = (pct or 0) - expected
    return {"expected": expected, "over": over, "state": state_for(over)}


def window_pace(reset_ts, pct, now=None):
    """The same for the five-hour window, where the budget is simply linear.

    There is no weekend in five hours, and no reason to spend it unevenly.
    """
    now = time.time() if now is None else now
    elapsed = min(FIVE_HOUR_SECONDS,
                  max(0.0, now - (reset_ts - FIVE_HOUR_SECONDS)))
    expected = elapsed / FIVE_HOUR_SECONDS * 100
    over = (pct or 0) - expected
    return {"expected": expected, "over": over, "state": state_for(over)}


def colour_state(pct, pace):
    """The state a display should colour by: the pace, floored by the level.

    See the module docstring - pace alone goes green at 95% when the burn
    matches the budget, and that is the figure most worth a warning.
    """
    if (pct or 0) >= LEVEL_FLOOR_PCT:
        return FAST
    return pace["state"] if pace else OK


def pace_for(pct, reset_ts, weekly=False, now=None):
    """Both numbers a display needs for one window, or None without a reset.

    A missing or zero reset timestamp means the window's start is unknown, so
    there is no budget to compare against and nothing honest to draw.
    """
    if not reset_ts:
        return None
    pace = weekly_pace(reset_ts, pct, now) if weekly else window_pace(
        reset_ts, pct, now)
    pace["colour_state"] = colour_state(pct, pace)
    return pace

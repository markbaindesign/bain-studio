from datetime import date

from studio.critical_path import Item, critical_items, wd_add, wd_diff, wd_count

D = date.fromisoformat


# --- working days -------------------------------------------------------------

def test_wd_add_skips_the_weekend():
    assert wd_add(D("2026-11-20"), 1) == D("2026-11-23")   # Fri -> Mon
    assert wd_add(D("2026-11-23"), -1) == D("2026-11-20")  # Mon -> Fri
    assert wd_add(D("2026-11-18"), 0) == D("2026-11-18")


def test_wd_diff_counts_working_days_and_is_signed():
    assert wd_diff(D("2026-11-20"), D("2026-11-23")) == 1
    assert wd_diff(D("2026-11-23"), D("2026-11-20")) == -1
    assert wd_diff(D("2026-11-16"), D("2026-11-16")) == 0


def test_wd_count_is_inclusive():
    assert wd_count(D("2026-11-16"), D("2026-11-20")) == 5
    assert wd_count(D("2026-11-16"), D("2026-11-16")) == 1


# --- the path -----------------------------------------------------------------

def chain():
    """Two routes into one milestone: a tight one and one with slack.

    long (Mon 16 - Thu 19) -> launch (Fri 20)
    short (Mon 16 - Tue 17) -> launch
    """
    return {
        "long": Item("long", "Long build", D("2026-11-19"), D("2026-11-16")),
        "short": Item("short", "Short task", D("2026-11-17"), D("2026-11-16")),
        "launch": Item("launch", "Launch", D("2026-11-20"), milestone=True,
                       blockers=["long", "short"]),
    }


def test_the_tight_route_is_critical_and_the_loose_one_is_not():
    crit, slack, target = critical_items(chain())
    assert target == "launch"
    assert crit == {"long", "launch"}
    assert slack["short"] == 2


def test_the_target_is_the_latest_milestone():
    items = chain()
    items["early"] = Item("early", "Early gate", D("2026-11-18"), milestone=True)
    _, _, target = critical_items(items)
    assert target == "launch"


def test_with_buffer_everywhere_the_tightest_chain_still_drives():
    # Both routes have slack before the milestone; the long one has less.
    items = chain()
    items["launch"].due = D("2026-11-25")
    crit, slack, _ = critical_items(items)
    assert slack["long"] < slack["short"]
    assert crit == {"long", "launch"}


def test_items_that_do_not_lead_to_the_target_are_ignored():
    items = chain()
    items["stray"] = Item("stray", "Unlinked", D("2026-11-20"), D("2026-11-16"))
    crit, slack, _ = critical_items(items)
    assert "stray" not in slack and "stray" not in crit


def test_slack_flows_back_through_milestones():
    # a (Mon-Tue) -> gate (Wed) -> b (Thu-Fri) -> end (Mon 23)
    items = {
        "a": Item("a", "A", D("2026-11-17"), D("2026-11-16")),
        "gate": Item("gate", "Gate", D("2026-11-18"), milestone=True, blockers=["a"]),
        "b": Item("b", "B", D("2026-11-20"), D("2026-11-19"), blockers=["gate"]),
        "end": Item("end", "End", D("2026-11-23"), milestone=True, blockers=["b"]),
    }
    crit, _, _ = critical_items(items)
    assert crit == {"a", "gate", "b", "end"}


def test_a_blocker_due_the_same_day_as_its_milestone_shows_negative_slack():
    items = {
        "t": Item("t", "Task", D("2026-11-20"), D("2026-11-16")),
        "m": Item("m", "Gate", D("2026-11-20"), milestone=True, blockers=["t"]),
    }
    crit, slack, _ = critical_items(items)
    assert slack["t"] == -1 and "t" in crit


def test_a_dependency_cycle_is_refused():
    import pytest
    items = chain()
    items["long"].blockers = ["launch"]
    with pytest.raises(ValueError, match="cycle"):
        critical_items(items)


def test_no_milestone_means_no_path():
    assert critical_items({"t": Item("t", "T", D("2026-11-20"))}) == (set(), {}, None)

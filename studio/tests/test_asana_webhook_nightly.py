"""Nightly sweep selection (BSTD-895): which tasks in unwatched projects get a run."""

from asana_webhook_logic import looper_claimed, nightly_wakes

BOT = "100"
MARK = "200"
PMBOT = "300"
CLIENT = "400"
TRIGGERS = {MARK, PMBOT}
CUTOFF = "2026-11-10T00:00:00"


def task(assignee=BOT, completed=False, looper=None):
    t = {"gid": "T1", "completed": completed, "assignee": {"gid": assignee} if assignee else None}
    if looper is not None:
        t["custom_fields"] = [{"name": "Priority", "display_value": "High"},
                              {"name": "Looper Status", "display_value": looper}]
    return t


def story(who, at, sub="comment_added", html=""):
    return {"resource_subtype": sub, "created_by": {"gid": who}, "created_at": at, "html_text": html}


def mention(gid):
    return f'<body><a data-asana-gid="{gid}">@DevBot</a> over to you</body>'


def wakes(t, stories, since=""):
    return nightly_wakes(t, stories, TRIGGERS, BOT, since, CUTOFF)


# --- comments ---------------------------------------------------------------

def test_marks_unanswered_comment_on_a_bot_task_wakes():
    assert wakes(task(), [story(BOT, "2026-11-15T10:00:00Z"), story(MARK, "2026-11-18T21:00:00Z")])


def test_answered_comment_does_not_wake():
    assert not wakes(task(), [story(MARK, "2026-11-18T21:00:00Z"), story(BOT, "2026-11-18T21:05:00Z")])


def test_pmbot_comment_wakes_but_a_clients_does_not():
    assert wakes(task(), [story(PMBOT, "2026-11-18T21:00:00Z")])
    assert not wakes(task(), [story(CLIENT, "2026-11-18T21:00:00Z")])


def test_comment_before_the_last_wake_does_not_wake_again():
    assert not wakes(task(), [story(MARK, "2026-11-18T21:00:00Z")], since="2026-11-18T21:01:00Z")


def test_comment_older_than_the_lookback_does_not_wake():
    assert not wakes(task(), [story(MARK, "2026-11-01T09:00:00Z")])


def test_completed_task_never_wakes():
    assert not wakes(task(completed=True), [story(MARK, "2026-11-18T21:00:00Z")])


# --- handed-back tasks ------------------------------------------------------

def test_handed_back_task_wakes_only_on_a_mention_of_the_bot():
    t = task(assignee=MARK)
    assert not wakes(t, [story(MARK, "2026-11-18T21:00:00Z", html="<body>note to self</body>")])
    assert wakes(t, [story(MARK, "2026-11-18T21:00:00Z", html=mention(BOT))])


def test_a_mention_counts_only_on_the_newest_comment():
    t = task(assignee=MARK)
    assert not wakes(t, [story(MARK, "2026-11-17T21:00:00Z", html=mention(BOT)),
                         story(MARK, "2026-11-18T21:00:00Z", html="<body>never mind</body>")])


# --- assignment -------------------------------------------------------------

def test_task_assigned_to_the_bot_by_mark_wakes_with_no_comment():
    assert wakes(task(), [story(MARK, "2026-11-18T21:00:00Z", sub="assigned")])


def test_assignment_by_the_bot_itself_does_not_wake():
    # sync.py --create-task assigns as bainbot: a new backlog task is not a request.
    assert not wakes(task(), [story(BOT, "2026-11-18T21:00:00Z", sub="assigned")])


def test_assignment_story_ignored_once_the_task_is_mark_s():
    assert not wakes(task(assignee=MARK), [story(MARK, "2026-11-18T21:00:00Z", sub="assigned")])


def test_assignment_already_answered_does_not_wake():
    assert not wakes(task(), [story(MARK, "2026-11-18T21:00:00Z", sub="assigned"),
                              story(BOT, "2026-11-18T22:00:00Z")])


def test_other_story_types_are_not_triggers():
    assert not wakes(task(), [story(MARK, "2026-11-18T21:00:00Z", sub="section_changed")])


# --- looper -----------------------------------------------------------------

def test_looper_queued_and_in_progress_tasks_are_claimed():
    assert looper_claimed(task(looper="Queue"))
    assert looper_claimed(task(looper="In Progress"))


def test_other_looper_statuses_and_no_field_are_not_claimed():
    assert not looper_claimed(task(looper="Review"))
    assert not looper_claimed(task(looper="Blocked"))
    assert not looper_claimed(task(looper=""))
    assert not looper_claimed(task())

import importlib.machinery
import importlib.util
import json
import time
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "session-status"
_loader = importlib.machinery.SourceFileLoader("session_status", str(SCRIPT))
_spec = importlib.util.spec_from_loader("session_status", _loader)
s = importlib.util.module_from_spec(_spec)
_loader.exec_module(s)

NOW = time.time()


def assistant(stop_reason, tool_use=False, usage=None):
    content = [{"type": "text", "text": "hi"}]
    if tool_use:
        content.append({"type": "tool_use", "name": "Bash", "input": {}})
    message = {"role": "assistant", "content": content, "stop_reason": stop_reason}
    if usage:
        message["usage"] = usage
    return json.dumps({"type": "assistant", "message": message})


def user(text="go"):
    return json.dumps({"type": "user", "message": {"role": "user", "content": text}})


# --- has the turn finished? ------------------------------------------------

def test_assistant_end_turn_is_finished():
    assert s.scan([user(), assistant("end_turn")])["finished"]


def test_outstanding_tool_use_is_not_finished():
    assert not s.scan([user(), assistant("tool_use", tool_use=True)])["finished"]


def test_prompt_after_a_finished_turn_is_not_finished():
    """The bug this guards: a new prompt arrives and the model is thinking, so
    the newest assistant entry is still the *previous* turn's end_turn. Reading
    stop_reason alone called that finished - 13 of 145 turn-starts on one real
    transcript."""
    assert not s.scan([user(), assistant("end_turn"), user()])["finished"]


def test_tool_result_mid_turn_is_not_finished():
    # A tool result is a user entry too, and arrives while the turn is live.
    lines = [user(), assistant("tool_use", tool_use=True), user("<tool_result>")]
    assert not s.scan(lines)["finished"]


def test_finished_again_after_the_next_turn_ends():
    lines = [user(), assistant("end_turn"), user(), assistant("end_turn")]
    assert s.scan(lines)["finished"]


def test_blob_lines_between_entries_are_ignored():
    blob = json.dumps({"type": "api-request-blob", "base": "x" * 50})
    assert s.scan([user(), blob, assistant("end_turn"), blob])["finished"]


def test_no_turn_seen_is_reported():
    assert not s.scan([json.dumps({"type": "api-request-blob"})])["seen_turn"]


# --- context size ----------------------------------------------------------

def test_context_sums_the_four_usage_fields():
    usage = {"input_tokens": 2, "cache_read_input_tokens": 279415,
             "cache_creation_input_tokens": 2142, "output_tokens": 1187}
    # Matches the 283.2k the session's own footer reported.
    assert s.scan([assistant("end_turn", usage=usage)])["ctx"] == 282746


def test_context_is_zero_without_usage():
    assert s.scan([assistant("end_turn")])["ctx"] == 0


def test_tokens_formats_thousands():
    assert s.tokens(282746) == "282k"
    assert s.tokens(0) == "-"
    assert s.tokens(840) == "840"


# --- title -----------------------------------------------------------------

def test_latest_ai_title_wins():
    first = json.dumps({"type": "ai-title", "aiTitle": "Old"})
    second = json.dumps({"type": "ai-title", "aiTitle": "New"})
    assert s.scan([first, second])["title"] == "New"


# --- fitting the row to the pane ------------------------------------------

ROW = {"status": "shell", "account": "bain", "where": "studio:1.0",
       "project": "middlewayeducation", "ctx": 282744, "ctx_pct": 63,
       "model": "Opus 5.5", "for": 480, "title": "Invoices bookkeeping"}


def test_row_never_exceeds_the_pane():
    for width in range(30, 200):
        assert len(s.row_text(ROW, width, True)) < width


def test_narrow_row_keeps_status_target_and_time():
    text = s.row_text(ROW, 60, True)
    assert "shell" in text and "studio:1.0" in text and "8m" in text


def test_context_is_dropped_before_the_time_column():
    text = s.row_text(ROW, 46, True)
    assert "282k" not in text
    assert "8m" in text


def test_percentage_and_model_go_before_the_token_count():
    """Order of sacrifice as the pane narrows: percentage, then model, then the
    token count, which is the one that is always there to give."""
    assert "63%" in s.row_text(ROW, 120, True)
    assert "63%" not in s.row_text(ROW, 64, True)
    assert "o5.5" in s.row_text(ROW, 64, True)
    assert "o5.5" not in s.row_text(ROW, 60, True)
    assert "282k" in s.row_text(ROW, 60, True)


def test_a_missing_percentage_does_not_shift_the_columns():
    """Fixed-width columns even when empty: the pane is read as a block, and a
    session that has not reported one must not pull the rest of its row left."""
    blank = dict(ROW, ctx_pct=0, model="")
    assert len(s.row_text(blank, 120, True)) == len(s.row_text(ROW, 120, True))


# --- the model column ------------------------------------------------------

def test_model_is_shortened_to_initial_and_version():
    assert s.short_model("Opus 5.5") == "o5.5"
    assert s.short_model("Sonnet 5") == "s5"
    assert s.short_model("Haiku 5.5") == "h5.5"


def test_an_unversioned_model_keeps_its_initial():
    assert s.short_model("Opus") == "o"
    assert s.short_model("") == ""


# --- the quota line --------------------------------------------------------

def quota(**kwargs):
    base = {"account": "bain", "pct": 40, "reset_ts": NOW + 3600,
            "weekly_pct": 64, "weekly_reset_ts": NOW + 3 * 86400}
    base.update(kwargs)
    return base


def test_quota_line_shows_both_windows():
    text, _ = s.quota_text([quota()])
    assert "bain" in text and "5h 40%" in text and "wk 64%" in text


def test_a_rolled_over_window_is_not_quoted():
    """The snapshot is only written when a status line renders. Once its reset
    time has passed the percentage belongs to a window that is gone, and 99%
    from an hour ago would read as 99% now."""
    text, worst = s.quota_text([quota(pct=99, reset_ts=NOW - 60, weekly_pct=10)])
    assert "99%" not in text and "5h reset" in text
    assert worst == 10


def test_a_rolled_over_week_is_not_quoted_either():
    """The likelier of the two: an account left unused past its weekly reset
    keeps last week's figure, and a high one would colour the whole line."""
    text, worst = s.quota_text(
        [quota(pct=20, weekly_pct=96, weekly_reset_ts=NOW - 3600)])
    assert "96%" not in text and "wk reset" in text
    assert worst == 20


def test_a_weekly_reset_within_the_day_gets_a_clock_time():
    # "->Fri" on a Friday reads as next Friday.
    soon, _ = s.quota_text([quota(weekly_reset_ts=NOW + 3600)])
    later, _ = s.quota_text([quota(weekly_reset_ts=NOW + 3 * 86400)])
    assert ":" in soon.split("wk")[1]
    assert ":" not in later.split("wk")[1]


def test_a_missing_reset_time_is_left_out_rather_than_formatted():
    # An unset timestamp would format as the epoch and read as a clock time.
    text, _ = s.quota_text([quota(reset_ts=0, weekly_reset_ts=0)])
    assert "5h 40%" in text and "\u2192" not in text


def test_quota_severity_is_the_worst_figure_of_any_account():
    """Either window of either account can be the one that stops work, so the
    line is coloured by whichever is worst - and the figure is returned rather
    than a colour, because curses will not hand out a pair without a screen."""
    _, weekly = s.quota_text([quota(pct=10, weekly_pct=82)])
    _, five = s.quota_text([quota(pct=95, weekly_pct=10)])
    _, second_account = s.quota_text([quota(pct=10, weekly_pct=10),
                                      quota(account="kf", pct=91, weekly_pct=3)])
    assert weekly == 82 and five == 95 and second_account == 91


def test_every_account_appears_on_the_quota_line():
    text, _ = s.quota_text([quota(), quota(account="kf", pct=4, weekly_pct=11)])
    assert "bain" in text and "kf" in text


# --- the per-session snapshot ----------------------------------------------

def test_snapshot_reads_the_model_and_context_percentage(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "SNAPSHOTS", tmp_path)
    (tmp_path / "abc.json").write_text(json.dumps(
        {"model": "Opus 5.5", "last_context_pct": 63, "cost_usd": 1.2}))
    assert s.snapshot("abc") == {"model": "Opus 5.5", "ctx_pct": 63}


def test_a_session_with_no_snapshot_yet_is_empty_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "SNAPSHOTS", tmp_path)
    assert s.snapshot("nothing-here") == {}


def test_title_only_appears_when_there_is_room():
    assert "Invoices bookkeeping" not in s.row_text(ROW, 76, True)
    assert "Invoices bookkeeping" in s.row_text(ROW, 120, True)


def test_sort_is_attention_then_live_work_then_parked():
    order = ["waiting", "shell", "busy", "idle"]
    assert [s.STATUS_ORDER[name] for name in order] == [0, 1, 2, 3]


def test_idle_sorts_last():
    # A session idle for two days is asking for nothing; busy is worth watching.
    assert s.STATUS_ORDER["idle"] > s.STATUS_ORDER["busy"]


# --- the pulse -------------------------------------------------------------

def test_waiting_pulses_every_tick():
    assert s.glyph_for("waiting", 0) == s.GLYPH["waiting"]
    assert s.glyph_for("waiting", 1) == s.PULSE_OFF
    assert s.glyph_for("waiting", 2) == s.GLYPH["waiting"]


def test_shell_pulses_more_slowly_than_waiting():
    # Holds for three ticks either side, so it reads as a slower breath.
    assert [s.glyph_for("shell", f) for f in range(3)] == [s.GLYPH["shell"]] * 3
    assert [s.glyph_for("shell", f) for f in range(3, 6)] == [s.PULSE_OFF] * 3


def test_busy_spins_clockwise_through_four_quadrants():
    assert [s.glyph_for("busy", f) for f in range(5)] == list("◴◷◶◵◴")


def test_a_spinning_busy_never_wears_another_status_glyph():
    # ◐ is busy at rest, ◑ is shell, ◦ is a pulse's off-frame: none may show up
    # mid-rotation, or a glance would read the wrong status.
    spun = {s.glyph_for("busy", f) for f in range(8)}
    assert not spun & {s.GLYPH["shell"], s.GLYPH["waiting"], s.PULSE_OFF}


def test_idle_never_moves():
    for frame in range(12):
        assert s.glyph_for("idle", frame) == s.GLYPH["idle"]


def test_busy_counts_as_animating_so_the_screen_ticks_for_it():
    assert "busy" in s.ANIMATED and "idle" not in s.ANIMATED


def test_pulse_reaches_the_rendered_row():
    waiting = dict(ROW, status="waiting")
    assert s.row_text(waiting, 120, True, 0).startswith(s.GLYPH["waiting"])
    assert s.row_text(waiting, 120, True, 1).startswith(s.PULSE_OFF)

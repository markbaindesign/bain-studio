import importlib.machinery
import importlib.util
import json
import re
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


def test_sort_is_blocked_then_parked_then_working():
    order = ["waiting", "shell", "idle", "working"]
    assert [s.STATUS_ORDER[name] for name in order] == [0, 1, 2, 3]


def test_working_sorts_last():
    # A session mid-turn is asking for nothing; an idle one may want picking up.
    assert s.STATUS_ORDER["working"] > s.STATUS_ORDER["idle"]


# --- the pulse -------------------------------------------------------------

def test_waiting_pulses_every_tick():
    assert s.glyph_for("waiting", 0) == s.GLYPH["waiting"]
    assert s.glyph_for("waiting", 1) == s.PULSE_OFF
    assert s.glyph_for("waiting", 2) == s.GLYPH["waiting"]


def test_shell_pulses_more_slowly_than_waiting():
    # Holds for three ticks either side, so it reads as a slower breath.
    assert [s.glyph_for("shell", f) for f in range(3)] == [s.GLYPH["shell"]] * 3
    assert [s.glyph_for("shell", f) for f in range(3, 6)] == [s.PULSE_OFF] * 3


def test_working_spins_clockwise_through_four_quadrants():
    assert [s.glyph_for("working", f) for f in range(5)] == list("◴◷◶◵◴")


def test_a_spinning_working_never_wears_another_status_glyph():
    # ◐ is working at rest, ◑ is shell, ◦ is a pulse's off-frame: none may show
    # up mid-rotation, or a glance would read the wrong status.
    spun = {s.glyph_for("working", f) for f in range(8)}
    assert not spun & {s.GLYPH["shell"], s.GLYPH["waiting"], s.PULSE_OFF}


def test_idle_never_moves():
    for frame in range(12):
        assert s.glyph_for("idle", frame) == s.GLYPH["idle"]


def test_working_counts_as_animating_so_the_screen_ticks_for_it():
    assert "working" in s.ANIMATED and "idle" not in s.ANIMATED


def test_pulse_reaches_the_rendered_row():
    waiting = dict(ROW, status="waiting")
    assert s.row_text(waiting, 120, True, 0).startswith(s.GLYPH["waiting"])
    assert s.row_text(waiting, 120, True, 1).startswith(s.PULSE_OFF)


# --- the column legend -----------------------------------------------------

def test_header_breaks_at_the_same_columns_as_a_row():
    """The legend is only worth having if it sits over the right columns, at
    every width where a column is dropped."""
    for width in (50, 80, 140):
        header = s.header_text(width, True)
        row = s.row_text(ROW, width, True)
        assert header.index("where") == row.index("studio:1.0")
        # Prefix, not the whole name: a narrow pane clips the project column.
        assert header.index("project") == row.index("middleway")
        if "282k" in row:
            # Numbers and their labels are both right-aligned, so it is the
            # right-hand edges that have to meet.
            assert header.index("ctx") + 3 == row.index("282k") + 4
            assert header.index("last") + 4 == row.index("8m") + 2


def test_header_never_exceeds_the_pane():
    for width in range(30, 200):
        assert len(s.header_text(width, True)) < width


def test_header_names_only_the_columns_that_fit():
    assert "ctx%" in s.header_text(140, True)
    assert "ctx%" not in s.header_text(64, True)
    assert "model" not in s.header_text(60, True)
    assert "status" in s.header_text(60, True)


def test_header_drops_the_account_label_with_the_account_column():
    assert "acct" in s.header_text(140, True)
    assert "acct" not in s.header_text(140, False)


# --- what the CLI calls busy ----------------------------------------------

def _one_session(monkeypatch, finished):
    """collect() over a single live session, with everything it reads stubbed."""
    monkeypatch.setattr(s, "pane_by_pid", lambda: {})
    monkeypatch.setattr(s, "sessions", lambda: [
        {"pid": 1, "sessionId": "abc", "status": "busy", "cwd": "/tmp/p",
         "kind": "interactive", "_account": "bain", "startedAt": NOW}])
    monkeypatch.setattr(s, "transcript", lambda *a: Path("/nonexistent"))
    monkeypatch.setattr(s, "last_activity", lambda *a: NOW)
    monkeypatch.setattr(s, "transcript_state",
                        lambda *a: {"finished": finished, "ctx": 0, "title": ""})
    monkeypatch.setattr(s, "snapshot", lambda *a: {})
    monkeypatch.setattr(s, "locate", lambda *a: "-")
    monkeypatch.setattr(s.Path, "exists", lambda self: True)
    return s.collect()[0]["status"]


def test_a_cli_busy_session_mid_turn_is_shown_as_working(monkeypatch):
    assert _one_session(monkeypatch, finished=False) == "working"


def test_a_cli_busy_session_whose_turn_is_over_is_still_shell(monkeypatch):
    # A live background shell holding the CLI at busy is the case this exists for.
    assert _one_session(monkeypatch, finished=True) == "shell"


# --- the conky panel mode -------------------------------------------------

def _row(status="idle", **over):
    row = {"status": status, "ctx": 118000, "ctx_pct": 12, "model": "Opus 5.5",
           "title": "Passiko project setup", "account": "bain",
           "where": "mwe:1.1", "project": "middlewayeducation", "for": 720}
    row.update(over)
    return row


def _quota(pct=10, weekly=20):
    return {"account": "bain", "pct": pct, "reset_ts": NOW + 3600,
            "weekly_pct": weekly, "weekly_reset_ts": NOW + 200000}


def test_a_card_is_three_lines():
    # The card height is what decides how many sessions the column holds.
    assert len(s.conky_card(_row(), False)) == s.CONKY_CARD_LINES == 3


def test_nothing_in_a_card_blinks():
    # ${blink} was tried on the glyph and shifted the rest of the line
    # sideways in its off phase. The pulse lives on the card's bar instead.
    for status in ("waiting", "shell", "idle", "working"):
        assert "${blink" not in "".join(s.conky_card(_row(status), False))


def test_only_waiting_is_flagged_to_pulse(monkeypatch):
    written = []
    monkeypatch.setattr(s, "collect",
                        lambda: [_row("waiting"), _row("idle")])
    monkeypatch.setattr(s, "quotas", lambda: [])
    monkeypatch.setattr(s, "write_card_state", lambda rects: written.extend(rects))
    s.emit_conky()
    assert [rect[3] for rect in written] == [1, 0]


def test_each_status_keeps_its_own_colour():
    for status, colour in s.CONKY_STATUS_COLOUR.items():
        assert colour in "".join(s.conky_card(_row(status), False))


def test_a_dollar_in_a_title_is_escaped():
    # conky reads $ as its variable sigil, so an unescaped title would swallow
    # the rest of the line.
    out = "".join(s.conky_card(_row(title="fix $HOME in deploy"), False))
    assert "$$HOME" in out
    assert "$HOME" not in out.replace("$$HOME", "")


def test_the_account_label_appears_only_with_two_accounts():
    assert "bain" in "".join(s.conky_card(_row(), True))
    assert "bain" not in "".join(s.conky_card(_row(), False))


def test_the_glyph_is_drawn_in_a_font_that_has_it():
    # Roboto Mono for Powerline has no U+25D0-25D1 and conky's Xft takes no
    # fallback list, so the glyph has to name its own family.
    head = s.conky_card(_row("working"), False)[0]
    assert "${font DejaVu Sans Mono" in head
    assert head.count("${font}") == 1


def test_every_line_of_a_card_starts_on_the_same_column():
    # The body lines are placed with ${goto}, which measures from the window
    # edge, not from the text area - so they have to repeat the inner margin
    # or they slide under the card's status bar.
    assert s.CARD_BODY_X == s.CONKY_TEXT_LEFT
    for line in s.conky_card(_row(), False)[1:]:
        assert line.startswith("${goto %d}" % s.CONKY_TEXT_LEFT)


# --- the card rectangles handed to the Lua hook ---------------------------

def test_card_rectangles_match_the_offsets_the_text_is_given():
    # The invariant the whole split rests on: the gap fed to conky as
    # ${voffset} and the gap used to place the rectangle are the same number,
    # so a card cannot drift away from the text it sits behind.
    first_top, height = s.card_rect(0, 5)
    second_top, _ = s.card_rect(1, 5)
    assert height == (3 * s.CONKY_LINE_HEIGHT) + (2 * s.CONKY_CARD_PAD)
    assert second_top - first_top == height + s.CONKY_CARD_GAP


def test_the_first_card_sits_below_the_header():
    top, _ = s.card_rect(0, 5)
    assert top == s.CONKY_TEXT_TOP + 5 * s.CONKY_LINE_HEIGHT


def test_the_column_holds_a_busy_day():
    # 12 sessions have been seen at once; three-line cards were chosen to fit
    # more than that.
    assert s.card_capacity(5) >= 13


def test_the_state_file_is_what_the_lua_hook_parses(tmp_path):
    # studio-claude-bg.lua matches "^(%d+) (%d+) (%x%x%x%x%x%x) (%d)$".
    path = tmp_path / "cards.txt"
    s.write_card_state([(110, 66, "f7768e", 1), (184, 66, "9ece6a", 0)], path)
    lines = path.read_text().splitlines()
    assert lines == ["110 66 f7768e 1", "184 66 9ece6a 0"]
    for line in lines:
        assert re.match(r"^\d+ \d+ [0-9a-f]{6} [01]$", line)


def test_an_unwritable_state_file_does_not_stop_the_panel(tmp_path):
    # The panel still reads correctly without its card surfaces.
    s.write_card_state([(1, 2, "f7768e", 0)], tmp_path / "no" / "such" / "x")


# --- the header -----------------------------------------------------------

def test_the_count_takes_the_colour_of_the_most_demanding_status():
    waiting = s.conky_header([_row("waiting"), _row("idle")], [])[0]
    assert s.CONKY_STATUS_COLOUR["waiting"] in waiting
    shell = s.conky_header([_row("shell"), _row("idle")], [])[0]
    assert s.CONKY_STATUS_COLOUR["shell"] in shell
    quiet = s.conky_header([_row("idle"), _row("working")], [])[0]
    assert s.CONKY_STATUS_COLOUR["waiting"] not in quiet


def test_the_shell_count_is_left_out_when_it_is_zero():
    assert "shell" not in s.conky_header([_row("idle")], [])[1]
    assert "1 shell" in s.conky_header([_row("shell")], [])[1]


def test_one_quota_line_per_account():
    two = [dict(_quota(), account="bain"), dict(_quota(), account="kf")]
    lines = s.conky_quota(two)
    assert len(lines) == 2
    assert "bain" in lines[0] and "kf" in lines[1]


def test_an_account_colours_on_its_own_worst_window():
    # One account going red must not drag the other with it.
    lines = s.conky_quota([dict(_quota(weekly=95), account="bain"),
                           dict(_quota(weekly=20), account="kf")])
    assert s.QUOTA_RED_HEX in lines[0]
    assert s.QUOTA_RED_HEX not in lines[1]
    assert s.QUOTA_AMBER_HEX in s.conky_quota([_quota(weekly=75)])[0]


def test_the_quota_arrow_is_drawn_in_the_glyph_font():
    assert "${font DejaVu Sans Mono" in s.conky_quota([_quota()])[0]


# --- overflow -------------------------------------------------------------

def test_more_sessions_than_fit_are_counted_not_dropped(monkeypatch):
    # A session that is not on screen must still be accounted for: the app
    # exists because a session can otherwise go unnoticed.
    monkeypatch.setattr(s, "collect", lambda: [_row() for _ in range(40)])
    monkeypatch.setattr(s, "quotas", lambda: [])
    monkeypatch.setattr(s, "write_card_state", lambda rects: None)
    out = []
    monkeypatch.setattr("builtins.print", lambda text: out.append(text))
    s.emit_conky()
    assert "more" in out[0]


def test_no_sessions_says_so(monkeypatch, capsys):
    monkeypatch.setattr(s, "collect", lambda: [])
    monkeypatch.setattr(s, "quotas", lambda: [])
    monkeypatch.setattr(s, "write_card_state", lambda rects: None)
    s.emit_conky()
    assert "no sessions" in capsys.readouterr().out

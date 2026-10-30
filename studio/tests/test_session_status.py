import importlib.machinery
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "session-status"
_loader = importlib.machinery.SourceFileLoader("session_status", str(SCRIPT))
_spec = importlib.util.spec_from_loader("session_status", _loader)
s = importlib.util.module_from_spec(_spec)
_loader.exec_module(s)


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

ROW = {"status": "shell", "account": "main", "where": "studio:1.0",
       "project": "middlewayeducation", "ctx": 282744, "for": 480,
       "title": "Invoices bookkeeping"}


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

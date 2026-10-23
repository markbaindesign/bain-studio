import hashlib
import hmac
from pathlib import Path

from asana_webhook_logic import (
    body_length_error,
    busy_sessions,
    candidate_events,
    config_dir_from_envrc,
    git_config_parameters,
    over_rate_limit,
    prefix_from_path,
    protected_path_denies,
    secret_read_denies,
    should_reregister,
    story_triggers,
    task_gid_for,
    task_is_for_bot,
    unanswered,
    verify_signature,
)

BOT = "100"
MARK = "200"
PMBOT = "300"
CLIENT = "400"
TRIGGERS = {MARK, PMBOT}


def comment_event(user, task="T1", story="S1"):
    return {"user": {"gid": user} if user else None, "action": "added",
            "resource": {"gid": story, "resource_type": "story"},
            "parent": {"gid": task, "resource_type": "task"}}


# ---------------------------------------------------------------------------
# verify_signature
# ---------------------------------------------------------------------------

def test_signature_valid():
    body = b'{"events":[]}'
    sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert verify_signature("s3cret", body, sig)


def test_signature_wrong_secret_or_tampered_body():
    body = b'{"events":[]}'
    sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert not verify_signature("other", body, sig)
    assert not verify_signature("s3cret", body + b" ", sig)


def test_signature_missing_parts_rejected():
    assert not verify_signature("", b"x", "abc")
    assert not verify_signature("s3cret", b"x", "")


# ---------------------------------------------------------------------------
# candidate_events
# ---------------------------------------------------------------------------

def test_comment_by_mark_or_pmbot_is_candidate():
    assert len(candidate_events([comment_event(MARK), comment_event(PMBOT)], TRIGGERS, BOT)) == 2


def test_bot_own_comment_never_triggers():
    assert candidate_events([comment_event(BOT)], TRIGGERS | {BOT}, BOT) == []


def test_client_comment_does_not_trigger():
    assert candidate_events([comment_event(CLIENT)], TRIGGERS, BOT) == []


def test_system_event_with_null_user_dropped():
    assert candidate_events([comment_event(None)], TRIGGERS, BOT) == []


def test_assignee_change_is_candidate_other_field_is_not():
    assignee = {"user": {"gid": MARK}, "action": "changed",
                "resource": {"gid": "T1", "resource_type": "task"}, "change": {"field": "assignee"}}
    due = dict(assignee, change={"field": "due_on"})
    assert candidate_events([assignee, due], TRIGGERS, BOT) == [assignee]


def test_task_added_to_project_is_candidate():
    e = {"user": {"gid": PMBOT}, "action": "added",
         "resource": {"gid": "T9", "resource_type": "task"},
         "parent": {"gid": "P1", "resource_type": "project"}}
    assert candidate_events([e], TRIGGERS, BOT) == [e]


def test_section_move_does_not_trigger():
    e = {"user": {"gid": MARK}, "action": "added",
         "resource": {"gid": "T9", "resource_type": "task"},
         "parent": {"gid": "S1", "resource_type": "section"}}
    assert candidate_events([e], TRIGGERS, BOT) == []


def test_task_gid_for_story_uses_parent():
    assert task_gid_for(comment_event(MARK, task="T7")) == "T7"
    assert task_gid_for({"resource": {"gid": "T8", "resource_type": "task"}}) == "T8"


# ---------------------------------------------------------------------------
# story_triggers / task_is_for_bot
# ---------------------------------------------------------------------------

def test_story_must_be_comment_by_trigger_user():
    assert story_triggers({"resource_subtype": "comment_added", "created_by": {"gid": MARK}}, TRIGGERS)
    assert not story_triggers({"resource_subtype": "assigned", "created_by": {"gid": MARK}}, TRIGGERS)
    assert not story_triggers({"resource_subtype": "comment_added", "created_by": {"gid": CLIENT}}, TRIGGERS)


def test_task_is_for_bot():
    assert task_is_for_bot({"completed": False, "assignee": {"gid": BOT}}, BOT)
    assert not task_is_for_bot({"completed": True, "assignee": {"gid": BOT}}, BOT)
    assert not task_is_for_bot({"completed": False, "assignee": {"gid": MARK}}, BOT)
    assert not task_is_for_bot({"completed": False, "assignee": None}, BOT)


# ---------------------------------------------------------------------------
# unanswered (catch-up)
# ---------------------------------------------------------------------------

def c(user, at):
    return {"resource_subtype": "comment_added", "created_by": {"gid": user}, "created_at": at}


def test_unanswered_when_mark_spoke_last():
    assert unanswered([c(BOT, "2026-10-22T10:00"), c(MARK, "2026-10-22T11:00")], TRIGGERS, BOT)


def test_answered_when_bot_replied_after():
    assert not unanswered([c(MARK, "2026-10-22T10:00"), c(BOT, "2026-10-22T11:00")], TRIGGERS, BOT)


def test_client_comment_alone_is_not_unanswered():
    assert not unanswered([c(CLIENT, "2026-10-22T11:00")], TRIGGERS, BOT)


def test_not_unanswered_if_already_woken_since():
    stories = [c(MARK, "2026-10-22T11:00")]
    assert not unanswered(stories, TRIGGERS, BOT, since="2026-10-22T11:05")


# ---------------------------------------------------------------------------
# busy_sessions
# ---------------------------------------------------------------------------

def test_busy_when_session_open_in_project_or_subfolder(tmp_path):
    root = tmp_path / "proj"
    (root / "sub").mkdir(parents=True)
    sessions = [{"pid": 1, "cwd": str(root / "sub"), "name": "a"},
                {"pid": 2, "cwd": str(tmp_path), "name": "outside"},
                {"pid": 3, "cwd": str(root), "name": "dead"}]
    busy = busy_sessions(sessions, root, pid_alive=lambda pid: pid != 3)
    assert [s["name"] for s in busy] == ["a"]


def test_sibling_folder_with_shared_prefix_is_not_busy(tmp_path):
    root = tmp_path / "kf-21"
    root.mkdir()
    (tmp_path / "kf-21-old").mkdir()
    sessions = [{"pid": 1, "cwd": str(tmp_path / "kf-21-old")}]
    assert busy_sessions(sessions, root, pid_alive=lambda pid: True) == []


# ---------------------------------------------------------------------------
# over_rate_limit
# ---------------------------------------------------------------------------

def test_rate_limit_counts_only_last_hour():
    now = 10_000.0
    assert over_rate_limit([now - 10, now - 20, now - 30], now, max_runs=3)
    assert not over_rate_limit([now - 10, now - 20, now - 4000], now, max_runs=3)


# ---------------------------------------------------------------------------
# config_dir_from_envrc / prefix_from_path
# ---------------------------------------------------------------------------

def test_config_dir_from_envrc_expands_home():
    home = Path("/home/x")
    assert config_dir_from_envrc("export CLAUDE_CONFIG_DIR=~/.claude-kf\n", home) == "/home/x/.claude-kf"
    assert config_dir_from_envrc('export CLAUDE_CONFIG_DIR="$HOME/.claude-kf"', home) == "/home/x/.claude-kf"
    assert config_dir_from_envrc("export OTHER=1", home) == ""


def test_prefix_from_path():
    assert prefix_from_path("/asana/BD") == "BD"
    assert prefix_from_path("/bstd/") == "BSTD"
    assert prefix_from_path("/asana/KF-WEB?x=1") == "KF-WEB"
    assert prefix_from_path("/") == ""


# --- run hardening (BSTD-838 review) -------------------------------------------

def test_body_length_error():
    cap = 1024
    assert body_length_error("512", cap) is None
    assert body_length_error(None, cap) is None          # heartbeat with no body
    assert body_length_error("1024", cap) is None
    assert body_length_error("1025", cap) == 413
    assert body_length_error("-1", cap) == 400
    assert body_length_error("abc", cap) == 400


def test_should_reregister_only_repairs_known_webhooks():
    dead = [{"gid": "W1", "active": False}]
    live = [{"gid": "W1", "active": True}]
    assert should_reregister(dead, {"webhook_gid": "W1"}) is True
    assert should_reregister([], {"webhook_gid": "W1"}) is True      # Asana deleted it
    assert should_reregister(live, {"webhook_gid": "W1"}) is False
    # Never registered: catch-up must not create a first registration (e.g. BD).
    assert should_reregister([], None) is False
    assert should_reregister([], {}) is False
    assert should_reregister(dead, {"secret": "s"}) is False


def test_git_config_parameters_disables_hooks_and_appends():
    assert git_config_parameters("") == "'core.hooksPath=/dev/null'"
    assert git_config_parameters("'user.name=x'") == "'user.name=x' 'core.hooksPath=/dev/null'"


def test_protected_path_denies_are_absolute_edit_rules():
    # Edit(path) covers Write too; Claude Code ignores Write(path) rules.
    assert protected_path_denies(Path("/srv/proj/")) == [
        "Edit(//srv/proj/.git/**)", "Edit(//srv/proj/.claude/**)", "Edit(//srv/proj/.envrc)"]


def test_secret_read_denies_cover_root_and_nested_env_and_wp_config():
    rules = secret_read_denies(Path("/srv/proj"))
    for r in ("Read(//srv/proj/.env)", "Read(//srv/proj/**/.env)",
              "Read(//srv/proj/**/.env.*)", "Read(//srv/proj/**/wp-config.php)"):
        assert r in rules
    assert all(r.startswith("Read(//srv/proj/") for r in rules)


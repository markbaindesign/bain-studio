import hashlib
import hmac
from pathlib import Path

from asana_webhook_logic import (
    body_length_error,
    candidate_events,
    config_dir_from_envrc,
    GIT_WRITE_DENIES,
    activity_from,
    denylist_hits,
    git_config_parameters,
    hit_usage_limit,
    idle_expired,
    launchable,
    mentions_user,
    over_rate_limit,
    prefix_from_path,
    project_edit_deny,
    protected_path_denies,
    run_allow_rules,
    run_name,
    secret_read_denies,
    should_reregister,
    story_triggers,
    task_gid_for,
    task_is_for_bot,
    unanswered,
    verify_signature,
    wakes_bot,
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
# Watching and run limits
# ---------------------------------------------------------------------------

def test_idle_expiry_counts_from_last_activity_or_start():
    assert not idle_expired({"since": 0, "last_activity": 1000}, 1000 + 1799, 1800)
    assert idle_expired({"since": 0, "last_activity": 1000}, 1000 + 1800, 1800)
    assert idle_expired({"since": 100}, 100 + 1800, 1800)
    assert not idle_expired({"since": 100}, 100 + 60, 1800)


def test_launchable_one_run_per_task():
    # A task already running waits; its new comments are handled by one run after.
    assert launchable(["T1", "T2"], {"T1": "BD"}, {"T1": "BD", "T2": "BD"}, 2, 3) == ["T2"]


def test_launchable_caps_per_project_and_total():
    prefix_of = {"A1": "A", "A2": "A", "A3": "A", "B1": "B", "C1": "C"}
    assert launchable(["A1", "A2", "A3", "B1", "C1"], {}, prefix_of, 2, 3) == ["A1", "A2", "B1"]
    assert launchable(["B1", "C1"], {"A1": "A", "A2": "A", "X": "B"}, prefix_of, 2, 3) == []
    assert launchable(["A3", "B1"], {"A1": "A", "A2": "A"}, prefix_of, 2, 3) == ["B1"]


def test_run_name_prefers_local_id_and_is_branch_safe():
    assert run_name("123", {"123": "KF-WEB-42"}) == "KF-WEB-42"
    assert run_name("456", {}) == "456"
    assert run_name("7", {"7": "odd id/x"}) == "odd-id-x"


def test_run_allow_rules_edit_only_in_the_worktree():
    rules = run_allow_rules(Path("/data/wt/BD/BD-1"), Path("/ops/studio/sync.py"))
    assert "Edit(//data/wt/BD/BD-1/**)" in rules
    assert "Edit" not in rules and "Write" not in rules
    # One task read and one comment; never a project sync over Mark's mirror.
    assert "Bash(python3 /ops/studio/sync.py --get-task *)" in rules
    assert "Bash(python3 /ops/studio/sync.py --comment *)" in rules
    assert not any(r == "Bash(python3 /ops/studio/sync.py *)" for r in rules)
    # No branch switching or deleting from a worktree: it acts on the whole repo.
    assert not any("git branch" in r or "checkout" in r or "git flow" in r for r in rules)


def test_project_edit_deny_covers_the_whole_checkout():
    assert project_edit_deny(Path("/media/proj")) == ["Edit(//media/proj/**)"]


def test_usage_limit_detection():
    assert hit_usage_limit("Claude AI usage limit reached|1763400000")
    assert hit_usage_limit("You've hit your limit · resets at 6pm")
    assert not hit_usage_limit("Posted the Answer: comment. Done.")


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
        "Edit(//srv/proj/.git)", "Edit(//srv/proj/.git/**)", "Edit(//srv/proj/.claude/**)",
        "Edit(//srv/proj/.envrc)"]


def test_secret_read_denies_cover_root_and_nested_env_and_wp_config():
    rules = secret_read_denies(Path("/srv/proj"))
    for r in ("Read(//srv/proj/.env)", "Read(//srv/proj/**/.env)",
              "Read(//srv/proj/**/.env.*)", "Read(//srv/proj/**/wp-config.php)"):
        assert r in rules
    assert all(r.startswith("Read(//srv/proj/") for r in rules)



# ---------------------------------------------------------------------------
# Per-task worktrees (real git, temp repo)
# ---------------------------------------------------------------------------

import subprocess  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def repo(tmp_path, monkeypatch):
    import asana_webhook as aw
    root = tmp_path / "proj"
    root.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
           "GIT_CONFIG_PARAMETERS": "'core.hooksPath=/dev/null'"}
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    run = lambda *a, cwd=root: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)
    run("init", "-q")
    run("checkout", "-q", "-b", "main")
    (root / "f.txt").write_text("x")
    run("add", ".")
    run("commit", "-qm", "init")
    run("branch", "develop")
    monkeypatch.setattr(aw, "WORKTREES", tmp_path / "wts")

    class P:
        prefix = "BD"
    P.root = root
    return aw, P, run


def test_worktree_is_outside_the_project_on_a_bot_branch_from_develop(repo):
    aw, proj, run = repo
    wt, branch = aw.ensure_worktree(proj, "BD-7")
    assert branch == "bot/BD-7"
    assert not str(wt).startswith(str(proj.root))
    assert (wt / "f.txt").exists()
    # Reused by the next run on the same task.
    assert aw.ensure_worktree(proj, "BD-7") == (wt, branch)


def test_an_answer_leaves_nothing_behind(repo):
    aw, proj, run = repo
    wt, branch = aw.ensure_worktree(proj, "BD-8")
    assert aw.tidy_worktree(proj, wt, branch) == "removed (no changes)"
    assert not wt.exists()
    assert b"bot/BD-8" not in subprocess.run(["git", "branch"], cwd=proj.root,
                                             capture_output=True).stdout


def test_work_is_kept_for_review(repo):
    aw, proj, run = repo
    wt, branch = aw.ensure_worktree(proj, "BD-9")
    (wt / "g.txt").write_text("y")
    assert aw.tidy_worktree(proj, wt, branch) == "kept (uncommitted changes)"
    run("add", ".", cwd=wt)
    run("commit", "-qm", "work", cwd=wt)
    assert aw.tidy_worktree(proj, wt, branch) == "kept (1 commit(s) on bot/BD-9)"
    assert wt.exists()


def test_idle_project_waits_for_its_runs_then_stops(tmp_path, monkeypatch):
    import asana_webhook as aw
    monkeypatch.setattr(aw, "STATE", tmp_path)
    monkeypatch.setattr(aw, "WATCH", tmp_path / "watch.json")
    monkeypatch.setattr(aw, "LOG", tmp_path / "log")
    sent = []
    monkeypatch.setattr(aw, "_notify", lambda msg, prefix: sent.append(prefix))
    aw._locked_json(aw.WATCH, lambda d: d.update(BD={"since": 0, "last_activity": 0}))
    w = aw.Worker()
    w.pending = {"T2": {"prefix": "BD", "last": 0}}
    w.running = {"T1": {"prefix": "BD"}}
    w._expire(aw.watched())
    assert "BD" in aw.watched() and sent == []
    w.running = {}
    w._expire(aw.watched())
    assert "BD" not in aw.watched() and w.pending == {} and sent == ["BD"]


def test_only_marks_activity_keeps_a_project_watched():
    ev = lambda user: {"events": [{"user": {"gid": user}}], "source": "webhook"}
    assert activity_from(ev(MARK), MARK)
    assert not activity_from(ev(PMBOT), MARK)
    assert activity_from({"tasks": ["T1"], "source": "watch"}, MARK)


def test_denylist_hits_whole_words_only():
    terms = ["Acme", "acme.example", ""]
    assert denylist_hits("fix for ACME header", terms) == ["Acme"]
    assert denylist_hits("see acme.example/x", terms) == ["Acme", "acme.example"]
    assert denylist_hits("acmeish", terms) == []


def test_worktree_git_file_and_output_flag_are_denied():
    assert "Edit(//wt/BD-1/.git)" in protected_path_denies(Path("/wt/BD-1"))
    assert "Bash(git * --output*)" in GIT_WRITE_DENIES


def test_handed_back_task_wakes_the_bot_only_when_mentioned():
    html = f'<body><a data-asana-gid="{BOT}" data-asana-type="user"/> one more change</body>'
    assert mentions_user(html, BOT)
    assert not mentions_user("<body>one more change</body>", BOT)
    assert not mentions_user(f'<body><a data-asana-gid="{BOT}9"/></body>', BOT)
    mine = {"completed": False, "assignee": {"gid": MARK}}
    assert not wakes_bot(mine, BOT, mentioned=False)
    assert wakes_bot(mine, BOT, mentioned=True)
    assert wakes_bot({"completed": False, "assignee": {"gid": BOT}}, BOT, mentioned=False)
    assert not wakes_bot({"completed": True, "assignee": {"gid": BOT}}, BOT, mentioned=True)

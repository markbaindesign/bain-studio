"""Sandboxed execution for webhook runs (BSTD-896). The live check, which needs
bwrap, socat and a claude run, is studio/scripts/sandbox_probe.py."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asana_webhook_logic import (  # noqa: E402
    bot_test_command, exec_allow_rules, sandbox_missing, sandbox_settings,
)

HOME = Path("/home/u")
SYNC = Path("/s/studio/sync.py")


def settings(**kw):
    return sandbox_settings([Path("/p"), Path("/wt")], ["/reg", "/dbx"], HOME, SYNC, **kw)["sandbox"]


def test_missing_reports_each_absent_dependency():
    assert sandbox_missing(lambda c: None) == ["bwrap", "socat"]
    assert sandbox_missing(lambda c: "/usr/bin/" + c if c == "bwrap" else None) == ["socat"]
    assert sandbox_missing(lambda c: "/usr/bin/" + c) == []


def test_fails_closed_and_allows_nothing_by_itself():
    s = settings()
    assert s["enabled"] and s["failIfUnavailable"]
    assert s["autoAllowBashIfSandboxed"] is False
    assert s["allowUnsandboxedCommands"] is False
    assert s["network"]["allowedDomains"] == []


def test_secret_files_are_hidden_in_every_root_and_read_only_dir():
    deny = settings()["filesystem"]["denyRead"]
    for d in ("/p", "/wt", "/reg", "/dbx"):
        assert f"{d}/.env" in deny and f"{d}/**/.env" in deny and f"{d}/**/*.pem" in deny
    assert str(HOME / ".ssh") in deny
    assert str(HOME / ".claude/.credentials.json") in deny


def test_extra_secrets_added_and_blanks_skipped():
    deny = settings(extra_secrets=[Path("/state"), ""])["filesystem"]["denyRead"]
    assert "/state" in deny and "" not in deny


def test_read_only_dirs_are_not_writable():
    deny = settings()["filesystem"]["denyWrite"]
    assert "/reg" in deny and "/dbx" in deny
    s = sandbox_settings([Path("/p")], ["/reg", ""], HOME, SYNC)["sandbox"]
    assert "" not in s["filesystem"]["denyWrite"]


def test_git_claude_and_envrc_unwritable_in_every_root():
    deny = settings()["filesystem"]["denyWrite"]
    for d in ("/p", "/wt"):
        assert {f"{d}/.git", f"{d}/.claude", f"{d}/.envrc"} <= set(deny)


def test_strip_env_drops_listed_and_credential_named_keys():
    from asana_webhook_logic import strip_env
    env = {"PATH": "/bin", "HOME": "/h", "ASANA_PAT": "x", "OBSIDIAN_VAULT": "v",
           "HARVEST_TOKEN": "x", "WPE_API_PASSWORD": "x", "SLACK_WEBHOOK_URL": "x",
           "GOOGLE_SA_JSON": "x", "SOME_API_KEY": "x"}
    out = strip_env(env, ["OBSIDIAN_VAULT"])
    assert out == {"PATH": "/bin", "HOME": "/h"}


def test_only_git_and_two_sync_calls_leave_the_sandbox():
    ex = settings()["excludedCommands"]
    assert f"python3 {SYNC} --get-task *" in ex and f"python3 {SYNC} --comment *" in ex
    assert "git commit *" in ex and "git add *" in ex
    assert not any(e.startswith("python3 ") and str(SYNC) not in e for e in ex)
    assert not any(e.startswith(("git push", "git checkout", "git branch")) for e in ex)


def test_settings_serialise_for_the_command_line():
    json.loads(json.dumps(sandbox_settings([Path("/p")], [], HOME, SYNC)))


def test_exec_rules_add_the_project_test_command():
    assert "Bash(python3 *)" in exec_allow_rules()
    rules = exec_allow_rules("npm test")
    assert "Bash(npm test)" in rules and "Bash(npm test *)" in rules


def test_bot_test_command_from_claude_md():
    assert bot_test_command("x\nBOT_TEST_COMMAND: make test  \ny") == "make test"
    assert bot_test_command("no line here") == ""
    assert bot_test_command("") == ""

"""Confined bot runs in a git worktree of their own, outside the project.

Shared by the Asana webhook (studio/asana_webhook.py) and the nightly looper
(studio/scripts/looper_runner.py), so the two ways a bot works on a task are
confined the same way: the project's own checkout is never switched or written
to, so Mark's uncommitted work there can never ride along into a bot commit.

Stdlib plus asana_webhook_logic only. The looper runner imports this from the
ops deploy, where pulling in sync.py at import time would load another
checkout's .env and Asana helpers just to make a worktree.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from asana_webhook_logic import (  # noqa: E402
    GIT_WRITE_DENIES,
    config_dir_from_envrc,
    denylist_hits,
    git_config_parameters,
    project_edit_deny,
    protected_path_denies,
    read_only_dirs,
    run_allow_rules,
    secret_read_denies,
    strip_env,
)
from voice.tasks import OUTWARD_TOOLS  # noqa: E402

STUDIO_ROOT = Path(__file__).resolve().parents[1]
DATA_HOME = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share"))
# Not under bain-studio/: that folder holds the registry, which runs may read but
# never edit, and a deny on it would also deny the worktrees inside it.
WORKTREES = DATA_HOME / "bain-bot-worktrees"
REGISTRY_DIR = DATA_HOME / "bain-studio"
DENYLIST_PY = STUDIO_ROOT / "studio" / "scripts" / "gen-denylist.py"

DISALLOWED = OUTWARD_TOOLS + [
    "mcp__claude_ai_Asana",          # every Asana MCP tool: mutations go through sync.py
    "mcp__claude_ai_Gmail__create_draft",
    "WebFetch", "WebSearch",         # no network egress for a run that reads Asana comments
    "Bash(git flow * publish *)",
]

# Runs use --restricted (ADR 025): user, project and local settings files are ignored,
# so run_allow_rules() is the whole allow-list rather than an addition to the project's
# own. Only the tools in RUN_TOOLS exist; anything not allowed is denied.
RUN_TOOLS = "Read,Glob,Grep,Edit,Write,Bash"


def _git(cwd: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def base_branch(root: Path) -> str:
    """develop under git flow, else whatever the checkout's default branch is."""
    for name in ("develop", "main", "master"):
        if _git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0:
            return name
    return "HEAD"


def ensure_worktree(root: Path, wt: Path, branch: str) -> tuple:
    """(worktree path, branch), created at `wt` from the base branch on first use
    and reused by every later run that asks for the same path. `wt` must sit
    outside `root`. A branch can be checked out in only one worktree at a time,
    so each worktree needs a branch of its own."""
    if (wt / ".git").exists():
        return wt, branch
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git(root, "worktree", "prune")
    if _git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0:
        r = _git(root, "worktree", "add", str(wt), branch)
    else:
        r = _git(root, "worktree", "add", "-b", branch, str(wt), base_branch(root))
    if r.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {r.stderr.strip()}")
    return wt, branch


def guard_hits(root: Path, base: str, branch: str) -> list:
    """Run the client-data check on a bot branch of a repo that has the commit
    guard installed (the public tooling repos). Runs commit with hooks off, so
    the guard itself never saw these commits. [] for any other repo: a client's
    own repo legitimately names its client."""
    if not _git(root, "config", "core.hooksPath").stdout.strip():
        return []
    terms = subprocess.run([sys.executable, str(DENYLIST_PY)], capture_output=True, text=True)
    if terms.returncode != 0:
        return ["(denylist unavailable: check the branch by hand)"]
    added = "\n".join(l[1:] for l in _git(root, "diff", f"{base}..{branch}").stdout.splitlines()
                      if l.startswith("+") and not l.startswith("+++"))
    msgs = _git(root, "log", "--format=%B", f"{base}..{branch}").stdout
    return denylist_hits(added + "\n" + msgs, terms.stdout.splitlines())


def tidy_worktree(root: Path, wt: Path, branch: str) -> tuple:
    """Remove a run's worktree and branch when it changed nothing. Anything
    committed or left uncommitted stays for Mark. Returns (what was done, for
    the log; client-data hits on a kept branch, [] when there are none)."""
    if _git(wt, "status", "--porcelain").stdout.strip():
        return "kept (uncommitted changes)", []
    base = base_branch(root)
    ahead = _git(root, "rev-list", "--count", f"{base}..{branch}").stdout.strip()
    if ahead not in ("", "0"):
        hits = guard_hits(root, base, branch)
        if hits:
            return f"kept ({ahead} commit(s) on {branch}, CLIENT DATA: {hits[:5]})", hits
        return f"kept ({ahead} commit(s) on {branch})", []
    _git(root, "worktree", "remove", str(wt))
    _git(root, "branch", "-d", branch)
    return "removed (no changes)", []


def run_env(environ, root: Path, path_prefix: str = "", drop_keys=None) -> dict:
    """Environment for a confined run on Mark's Max login, in the project's own
    Claude account when its .envrc names one (KF runs on a separate account).

    With drop_keys (the webhook passes every key studio/.env defines), those
    keys and anything named like a credential are removed too, because a run
    that can execute code could read them from its environment (BSTD-896)."""
    env = dict(environ)
    if drop_keys is not None:
        env = strip_env(env, list(drop_keys))
    # sync.py loads studio/.env, which carries an API key for the Hermes
    # collectors. Left in, it outranks the claude.ai login and bills every run
    # to API credits instead of Mark's Max plan.
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        env.pop(key, None)
    prefix = f"{path_prefix}:" if path_prefix else ""
    env["PATH"] = f"{prefix}{Path.home() / '.local/bin'}:{env.get('PATH', '/usr/bin:/bin')}"
    envrc = root / ".envrc"
    cfg = config_dir_from_envrc(envrc.read_text() if envrc.exists() else "", Path.home())
    if cfg:
        env["CLAUDE_CONFIG_DIR"] = cfg
    # A run can write files and `git commit`; with hooks off, a hook it wrote can't run.
    env["GIT_CONFIG_PARAMETERS"] = git_config_parameters(env.get("GIT_CONFIG_PARAMETERS", ""))
    return env


def confined_argv(claude_bin: str, prompt: str, model: str, root: Path, wt: Path,
                  sync_py: Path, read_only: list, extra_dirs=(), extra_allow=(),
                  extra_deny=()) -> list:
    """The `claude -p` command line for a confined run: restricted settings, the
    allow-list from run_allow_rules (edits only inside `wt`), every edit in the
    project checkout denied, no network, no outward tools, credential files
    unreadable, and `read_only` folders readable but not writable. Never
    --dangerously-skip-permissions: anything not allowed is denied.

    extra_dirs are further working dirs (a factory product's worktree, BSTD-905),
    with their own extra_allow and extra_deny rules."""
    add_dirs, ro_denies = read_only_dirs(read_only)
    for d in extra_dirs:
        add_dirs += ["--add-dir", str(d)]
    return [claude_bin, "-p", prompt, "--model", model,
            "--restricted", "--strict-mcp-config", "--tools", RUN_TOOLS, *add_dirs,
            "--allowedTools", *run_allow_rules(wt, sync_py), *extra_allow,
            "--disallowedTools", *DISALLOWED, *GIT_WRITE_DENIES, *project_edit_deny(root),
            *protected_path_denies(root), *protected_path_denies(wt),
            *secret_read_denies(root), *secret_read_denies(wt), *ro_denies, *extra_deny]

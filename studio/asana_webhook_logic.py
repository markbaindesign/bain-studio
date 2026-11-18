#!/usr/bin/env python3
"""Pure logic for the Asana webhook listener (studio/asana_webhook.py).

Kept free of network and process calls so it can be unit-tested, following the
looper_logic.py pattern. The listener reads disk / the Asana API and hands the
results to these functions.

Covers:
  - X-Hook-Signature verification
  - Cheap pre-filtering of raw webhook events (no API calls)
  - Deciding whether a fetched story/task should wake an agent
  - Watching: the 30-minute idle rule, and which queued tasks may start under
    the per-project and global run limits
  - Per-task rate capping, to stop PmBot <-> DevBot ping-pong
  - Per-run worktree naming and the allow/deny rules that keep a run inside it
  - Reading a project's CLAUDE_CONFIG_DIR from its .envrc (ADR 017)
  - Run hardening: request size cap, catch-up re-registration rule, git hook
    override, protected-path deny rules

See studio/tests/test_asana_webhook.py.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------

def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    """True when `signature` is the hex SHA256 HMAC of the raw body under `secret`."""
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


# ---------------------------------------------------------------------------
# Event filtering
# ---------------------------------------------------------------------------

def candidate_events(events: list, trigger_users: set, bot_gid: str) -> list:
    """Drop events that can never wake an agent, before spending any API calls.

    Kept: a comment-like story added to a task, an assignee change on a task, or a
    task added to a project - and only when authored by a trigger user. System
    events (user null) and the bot's own events are dropped, which is what stops
    DevBot's own comments from waking DevBot.
    """
    out = []
    for e in events or []:
        user = (e.get("user") or {}).get("gid")
        if not user or user == bot_gid or user not in trigger_users:
            continue
        res = e.get("resource") or {}
        rtype = res.get("resource_type")
        action = e.get("action")
        parent_type = (e.get("parent") or {}).get("resource_type")
        if rtype == "story" and action == "added" and parent_type == "task":
            out.append(e)
        elif rtype == "task" and action == "changed" and (e.get("change") or {}).get("field") == "assignee":
            out.append(e)
        # A task moved between sections is "added" to a section; only a task added to
        # the project itself (i.e. created there) counts.
        elif rtype == "task" and action == "added" and parent_type == "project":
            out.append(e)
    return out


def task_gid_for(event: dict) -> str:
    """The task an event is about: the parent for a story, the resource for a task."""
    res = event.get("resource") or {}
    if res.get("resource_type") == "story":
        return (event.get("parent") or {}).get("gid", "")
    return res.get("gid", "")


def story_triggers(story: dict, trigger_users: set) -> bool:
    """A fetched story wakes an agent only if it is a comment by a trigger user."""
    if story.get("resource_subtype") != "comment_added":
        return False
    return (story.get("created_by") or {}).get("gid") in trigger_users


def task_is_for_bot(task: dict, bot_gid: str) -> bool:
    """Open task currently assigned to the bot."""
    if task.get("completed"):
        return False
    return (task.get("assignee") or {}).get("gid") == bot_gid


def mentions_user(html_text: str, user_gid: str) -> bool:
    """Does a comment's rich text @-mention this user? Asana renders a mention
    as <a data-asana-gid="..."> with the user's GID."""
    if not html_text or not user_gid:
        return False
    return bool(re.search(r'data-asana-gid="' + re.escape(user_gid) + r'"', html_text))


def wakes_bot(task: dict, bot_gid: str, mentioned: bool) -> bool:
    """An open task wakes the bot when it is assigned to the bot, or when the
    comment @-mentions the bot. A Review or Done hands a task back to Mark, and
    his comments on it then wake nothing unless he mentions the bot (his call,
    2026-11-17)."""
    if task.get("completed"):
        return False
    return task_is_for_bot(task, bot_gid) or mentioned


def unanswered(stories: list, trigger_users: set, bot_gid: str, since: str = "") -> bool:
    """Catch-up check: is the latest trigger-user comment newer than the bot's
    latest comment (and newer than `since`, the last time we woke an agent)?"""
    last_trigger = ""
    last_bot = ""
    for s in stories or []:
        if s.get("resource_subtype") != "comment_added":
            continue
        who = (s.get("created_by") or {}).get("gid")
        at = s.get("created_at") or ""
        if who == bot_gid:
            last_bot = max(last_bot, at)
        elif who in trigger_users:
            last_trigger = max(last_trigger, at)
    return bool(last_trigger) and last_trigger > last_bot and last_trigger > (since or "")


# ---------------------------------------------------------------------------
# Concurrency and rate limits
# ---------------------------------------------------------------------------

def idle_expired(entry: dict, now: float, idle_s: int) -> bool:
    """A watched project stops being watched `idle_s` after Mark's last activity
    on its bot tasks. `last_activity` falls back to when watching started."""
    last = (entry or {}).get("last_activity") or (entry or {}).get("since") or 0
    return now - last >= idle_s


def launchable(pending: list, running: dict, prefix_of: dict,
               per_project: int, total: int) -> list:
    """Which pending task GIDs may start now, oldest first.

    `pending` is task GIDs in arrival order, `running` maps a running task GID to
    its prefix, `prefix_of` maps a pending GID to its prefix. A task already
    running waits: what arrives meanwhile is handled by one run after it ends.
    At most `per_project` runs per project and `total` across all of them, so a
    burst of comments cannot use up the Max window Mark is working in.
    """
    counts: dict = {}
    for prefix in running.values():
        counts[prefix] = counts.get(prefix, 0) + 1
    n = len(running)
    out = []
    for gid in pending:
        if n >= total:
            break
        prefix = prefix_of.get(gid)
        if gid in running or counts.get(prefix, 0) >= per_project:
            continue
        out.append(gid)
        counts[prefix] = counts.get(prefix, 0) + 1
        n += 1
    return out


def run_name(task_gid: str, local_ids: dict) -> str:
    """Branch and worktree name for a task: its local ID when the project's
    asana-ids.json knows it (bot/BSTD-842), else the GID."""
    lid = (local_ids or {}).get(task_gid) or task_gid
    return re.sub(r"[^A-Za-z0-9._-]", "-", lid)


def run_allow_rules(worktree: Path, sync_py: Path) -> list:
    """The whole allow-list for a run (runs are --restricted, so nothing is
    inherited). Reads anywhere, subject to the secret denies; edits only inside
    the run's own worktree, which sits outside the project, so the checkout Mark
    is working in is never touched. Git is limited to inspecting and committing
    on the branch the worktree already has: no checkout, no branch commands
    (`git branch -D develop` from a worktree deletes it for the whole repo)."""
    wt = "/" + str(worktree).rstrip("/")
    return [
        "Read", "Glob", "Grep",
        f"Edit({wt}/**)",
        # Read one task, post one comment. Not a project sync: that rewrites the
        # mirror Mark may be editing in his own session.
        f"Bash(python3 {sync_py} --get-task *)",
        f"Bash(python3 {sync_py} --comment *)",
        "Bash(git status *)", "Bash(git status)", "Bash(git diff *)", "Bash(git diff)",
        "Bash(git log *)", "Bash(git log)", "Bash(git show *)",
        "Bash(git add *)", "Bash(git commit *)",
    ]


def project_edit_deny(root: Path) -> list:
    """Deny every edit inside the project checkout. Deny beats allow, and the
    run's worktree is outside the root, so this costs the run nothing."""
    return [f"Edit(/{str(root).rstrip('/')}/**)"]


USAGE_LIMIT_RE = re.compile(
    r"usage limit|limit reached|rate[ _-]?limit(?:ed)?|you've hit your limit|resets at",
    re.IGNORECASE)


def hit_usage_limit(output_tail: str) -> bool:
    """Did a run stop because the Max window ran out? Read from the end of its log."""
    return bool(USAGE_LIMIT_RE.search(output_tail or ""))


def over_rate_limit(history: list, now: float, max_runs: int, window_s: int = 3600) -> bool:
    """`history` is the list of past run timestamps for one task."""
    recent = [t for t in history if now - t < window_s]
    return len(recent) >= max_runs


# ---------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------

def config_dir_from_envrc(text: str, home: Path) -> str:
    """Extract CLAUDE_CONFIG_DIR from a direnv .envrc, expanding ~ and $HOME."""
    m = re.search(r"^\s*export\s+CLAUDE_CONFIG_DIR=[\"']?([^\"'\s]+)", text or "", re.MULTILINE)
    if not m:
        return ""
    val = m.group(1).replace("$HOME", str(home)).replace("${HOME}", str(home))
    if val.startswith("~"):
        val = str(home) + val[1:]
    return val


# ---------------------------------------------------------------------------
# Run hardening (PmBot review, BSTD-838)
# ---------------------------------------------------------------------------

def body_length_error(content_length, max_bytes: int):
    """HTTP status to reject a request with before reading its body, or None.

    Checked before the signature, so an unauthenticated caller can't make the
    listener read an arbitrarily large body."""
    try:
        n = int(content_length or 0)
    except (TypeError, ValueError):
        return 400
    if n < 0:
        return 400
    if n > max_bytes:
        return 413
    return None


def should_reregister(hooks: list, entry: dict) -> bool:
    """Catch-up only repairs a webhook we registered before (a stored webhook_gid)
    that Asana has since disabled or deleted. A project that was never registered
    is left alone, so adding it to ASANA_WEBHOOK_PROJECTS never registers it on the
    next 07:45 run - first registration is always a manual `register`."""
    if not (entry or {}).get("webhook_gid"):
        return False
    return not any(h.get("active") for h in hooks or [])


def git_config_parameters(existing: str) -> str:
    """GIT_CONFIG_PARAMETERS for agent runs: disable every git hook.

    Uses the pre-2.31 'key=value' form (this machine runs git 2.25, which has no
    GIT_CONFIG_COUNT and rejects 'key'='value'). Appends to any existing value."""
    ours = "'core.hooksPath=/dev/null'"
    return f"{existing} {ours}".strip() if existing else ours


def protected_path_denies(root: Path) -> list:
    """Absolute deny rules for files that would let a run escalate: git internals
    (hooks), Claude settings, and the .envrc a later run reads CLAUDE_CONFIG_DIR
    from. `//` marks an absolute path. Edit(path) rules cover every file-editing
    tool, Write included; Claude Code ignores Write(path) rules."""
    base = "/" + str(root).rstrip("/")
    # .git is a directory in a checkout but a one-line file in a worktree.
    return [f"Edit({base}/.git)", f"Edit({base}/.git/**)", f"Edit({base}/.claude/**)",
            f"Edit({base}/.envrc)"]


# `git log/diff/show --output=<path>` writes a file anywhere, past the Edit rules.
GIT_WRITE_DENIES = ["Bash(git * --output*)", "Bash(git * -o *)"]


def activity_from(item: dict, user_gid: str) -> bool:
    """Does a queue item count as Mark's activity, keeping the project watched?
    His own events and the sweep `watch` does count; PmBot's do not (Mark's
    call, 2026-11-17: the timer measures whether he is still at work)."""
    if item.get("source") == "watch":
        return True
    return any(((e.get("user") or {}).get("gid")) == user_gid for e in item.get("events") or [])


def denylist_hits(text: str, terms: list) -> list:
    """Client-data terms found as whole words in `text`, case-insensitively: the
    check the public repos' commit hook makes, which a bot run's commit skips
    because runs switch hooks off."""
    out = []
    for t in terms:
        t = t.strip()
        if t and re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text or "", re.IGNORECASE):
            out.append(t)
    return out


SECRET_FILES = (".env", ".env.*", "wp-config.php", "deploy.config.sh", "*.pem")


def secret_read_denies(root: Path) -> list:
    """Absolute Read deny rules for credential files inside the project root. A run
    has no network, but it can post any text as an Asana comment, which clients can
    see - so an injected comment must not be able to have it read studio/.env and
    echo it back. Read rules also cover Grep and Glob."""
    base = "/" + str(root).rstrip("/")
    out = []
    for name in SECRET_FILES:
        out += [f"Read({base}/{name})", f"Read({base}/**/{name})"]
    return out


def prefix_from_path(path: str) -> str:
    """Route by the last path segment, so /asana/BD and /BD both resolve to BD
    (tailscale serve may or may not strip its mount path)."""
    seg = [p for p in (path or "").split("?")[0].split("/") if p]
    return seg[-1].upper() if seg else ""


def dropbox_folder(claude_md: str) -> str:
    """The project's Dropbox folder, from the DROPBOX_FOLDER: line its CLAUDE.md
    already carries for the restrict-to-project hook. "" when there is none."""
    m = re.search(r"^DROPBOX_FOLDER:\s*(\S.*?)\s*$", claude_md or "", re.MULTILINE)
    return m.group(1) if m else ""


def read_only_dirs(dirs: list) -> tuple:
    """(--add-dir args, deny rules) giving a run read access to `dirs` and no
    more. Restricted mode confines file tools to the working directories, so a
    folder outside the worktree must be added to be read at all; adding it also
    opens it to edits, which the Edit deny closes. Credential files stay denied.
    Mark's call, 2026-11-17: the bot may read the registry and the project's
    Dropbox, but a Dropbox write has no branch to review, so it asks instead."""
    add, deny = [], []
    for d in dirs:
        if not d:
            continue
        add += ["--add-dir", str(d)]
        deny += [f"Edit(/{str(d).rstrip('/')}/**)", *secret_read_denies(Path(d))]
    return add, deny

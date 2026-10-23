#!/usr/bin/env python3
"""Pure logic for the Asana webhook listener (studio/asana_webhook.py).

Kept free of network and process calls so it can be unit-tested, following the
looper_logic.py pattern. The listener reads disk / the Asana API and hands the
results to these functions.

Covers:
  - X-Hook-Signature verification
  - Cheap pre-filtering of raw webhook events (no API calls)
  - Deciding whether a fetched story/task should wake an agent
  - Detecting open Claude sessions in a project folder (the "never two
    sessions on one project" rule)
  - Per-task rate capping, to stop PmBot <-> DevBot ping-pong
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

def _inside(child: str, root: Path) -> bool:
    try:
        Path(child).resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def busy_sessions(sessions: list, project_root: Path, pid_alive) -> list:
    """Open Claude sessions whose working directory is inside `project_root`.

    `sessions` are the parsed ~/.claude*/sessions/*.json records; `pid_alive` is
    a callable so tests don't need real processes. Interactive sessions count:
    an idle session left open on a project still owns it.
    """
    out = []
    for s in sessions:
        cwd = s.get("cwd") or ""
        pid = s.get("pid")
        if cwd and pid and pid_alive(pid) and _inside(cwd, project_root):
            out.append(s)
    return out


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
    return [f"Edit({base}/.git/**)", f"Edit({base}/.claude/**)", f"Edit({base}/.envrc)"]


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

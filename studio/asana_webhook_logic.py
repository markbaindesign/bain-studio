#!/usr/bin/env python3
"""Pure logic for the Asana webhook listener (studio/asana_webhook.py).

Kept free of network and process calls so it can be unit-tested, following the
looper_logic.py pattern. The listener reads disk / the Asana API and hands the
results to these functions.

Covers:
  - X-Hook-Signature verification
  - Cheap pre-filtering of raw webhook events (no API calls)
  - Deciding whether a fetched story/task should wake an agent
  - Watching: the 30-minute idle rule, open Claude sessions that hold a watch,
    and which queued tasks may start under the per-project and global run limits
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


LOOPER_FIELD = "Looper Status"
LOOPER_CLAIMED = {"queue", "in progress"}


def looper_claimed(task: dict) -> bool:
    """Is the task queued for the studio looper (Looper Status Queue or In
    Progress)? The nightly sweep leaves those to the looper. Read from the task's
    own custom fields, not the SL mirror, which is only as fresh as its last sync."""
    for f in task.get("custom_fields") or []:
        if (f.get("name") or "").strip().lower() == LOOPER_FIELD.lower():
            return (f.get("display_value") or "").strip().lower() in LOOPER_CLAIMED
    return False


def nightly_wakes(task: dict, stories: list, trigger_users: set, bot_gid: str,
                  since: str = "", cutoff: str = "") -> bool:
    """Nightly sweep: would the listener have woken the bot on this task, had its
    project been watched, with nothing from the bot since?

    The newest trigger-user story decides. It is either a comment, or an
    assignment while the task is assigned to the bot (a task handed to DevBot with
    no comment). It must be newer than the bot's last comment, than `since` (the
    last wake) and than `cutoff`, so old threads are not revived. Then the listener's
    rule applies (wakes_bot): a task assigned to the bot wakes it on any of these, a
    handed-back task only on a comment that @-mentions the bot.
    """
    if task.get("completed"):
        return False
    assigned = task_is_for_bot(task, bot_gid)
    last_bot = ""
    latest = None
    for s in stories or []:
        who = (s.get("created_by") or {}).get("gid")
        sub = s.get("resource_subtype")
        at = s.get("created_at") or ""
        if who == bot_gid:
            if sub == "comment_added":
                last_bot = max(last_bot, at)
        elif who in trigger_users and (sub == "comment_added" or (sub == "assigned" and assigned)):
            if latest is None or at > (latest.get("created_at") or ""):
                latest = s
    if latest is None:
        return False
    at = latest.get("created_at") or ""
    if at <= last_bot or at <= (since or "") or at < (cutoff or ""):
        return False
    mentioned = (latest.get("resource_subtype") == "comment_added"
                 and mentions_user(latest.get("html_text"), bot_gid))
    return wakes_bot(task, bot_gid, mentioned)


# ---------------------------------------------------------------------------
# Concurrency and rate limits
# ---------------------------------------------------------------------------

def idle_expired(entry: dict, now: float, idle_s: int) -> bool:
    """A watched project stops being watched `idle_s` after Mark's last activity
    on its bot tasks. `last_activity` falls back to when watching started.

    A Claude session open in the project holds the watch however long Mark is
    quiet in Asana; closing it sets `last_activity`, so `idle_s` then counts
    from the close (see prune_sessions)."""
    if (entry or {}).get("sessions"):
        return False
    last = (entry or {}).get("last_activity") or (entry or {}).get("since") or 0
    return now - last >= idle_s


def prune_sessions(entry: dict, now: float, alive) -> bool:
    """Drop the sessions in a watch entry whose Claude process has gone.

    SessionEnd does not fire when Claude crashes or is killed, so the worker
    checks each recorded pid with `alive(pid)` rather than trusting the hook to
    say goodbye. A session that has gone counts as closing `now`, which starts
    the idle timer. Returns True when anything was dropped."""
    sessions = (entry or {}).get("sessions") or {}
    gone = [sid for sid, s in sessions.items() if not alive((s or {}).get("pid"))]
    for sid in gone:
        del sessions[sid]
    if gone:
        entry["last_activity"] = max(entry.get("last_activity") or 0, now)
    return bool(gone)


def is_bot_session(env: dict, cwd: str, worktrees: str) -> bool:
    """Is this Claude session a bot's rather than Mark's? Bot sessions never
    start or extend a watch: a webhook run (BAIN_BOT_RUN, set by _launch), a
    looper session (LOOPER_RUN_ID, set by the runner), or anything working in a
    bot worktree."""
    if (env or {}).get("BAIN_BOT_RUN") or (env or {}).get("LOOPER_RUN_ID"):
        return True
    return bool(cwd) and _inside(cwd, worktrees)


def _inside(path: str, root: str) -> bool:
    p, r = Path(path).resolve(), Path(root).resolve()
    return p == r or r in p.parents


def prefix_for_dir(cwd: str, roots: dict) -> str | None:
    """The registered project a directory belongs to: the one with the deepest
    root containing it, so a project nested inside another (SL in bain-studio)
    wins over its parent. `roots` maps prefix to project root."""
    best, depth = None, -1
    for prefix, root in (roots or {}).items():
        if root and cwd and _inside(cwd, str(root)):
            d = len(Path(str(root)).resolve().parts)
            if d > depth:
                best, depth = prefix, d
    return best


def claude_pid(chain: list) -> int | None:
    """The Claude process a hook runs under: the nearest ancestor named claude.
    `chain` is (pid, comm) pairs from the hook's parent upwards."""
    for pid, comm in chain or []:
        if (comm or "").strip() == "claude":
            return pid
    return None


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


def product_git_rules(worktree: Path) -> list:
    """Git allowances for a product repo's worktree (BSTD-905). The run's cwd is
    the project worktree, so the plain `git add *` rules act there; the product
    repo is reached with `git -C <path>`, enumerated command by command so that
    checkout, branch and the rest stay out exactly as they do for the project."""
    wt = str(worktree).rstrip("/")
    out = []
    for cmd in ("status", "diff", "log", "show", "add", "commit"):
        out.append(f"Bash(git -C {wt} {cmd} *)")
        if cmd in ("status", "diff", "log"):
            out.append(f"Bash(git -C {wt} {cmd})")
    return out


def milestone_codename(value: str) -> str:
    """The product codename in a Related Milestone value. The factory names its
    milestones "Display Name (codename)", e.g. "Contents May Differ (prototype-hall)";
    a bare value is taken as the codename itself."""
    v = (value or "").strip()
    m = re.search(r"\(([^()]+)\)\s*$", v)
    return (m.group(1) if m else v).strip()


def product_for_milestone(products: dict, milestone: str):
    """The factory product a task's Related Milestone names, or None. Only an
    `in-production` product with a source path qualifies: a graduated product is
    released and edited by hand, and anything else (unknown codename, no source,
    a malformed products.json) gets no second worktree. Matched on codename, not
    name, because a product's public name changes while its codename does not."""
    code = milestone_codename(milestone)
    if not code or code.lower() == "none" or not isinstance(products, dict):
        return None
    for p in products.get("products") or []:
        if not isinstance(p, dict):
            continue
        if p.get("codename") == code and p.get("status") == "in-production" and p.get("source"):
            return p
    return None


def custom_field_value(task: dict, name: str) -> str:
    """A task's custom field, as displayed, by field name. "" when absent."""
    for cf in (task or {}).get("custom_fields") or []:
        if (cf or {}).get("name") == name:
            return cf.get("display_value") or ""
    return ""


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


# ---------------------------------------------------------------------------
# Inbox poll: DevBot's tasks across every project, without a watch
# ---------------------------------------------------------------------------

def newly_assigned(task: dict, stories: list, trigger_users: set, bot_gid: str,
                   since: str = "") -> bool:
    """Was this task handed to the bot by Mark or PmBot since the bot last spoke on
    it and since it was last woken? Covers both a reassignment (an `assigned`
    story) and a task created already assigned to the bot (no such story)."""
    if not task_is_for_bot(task, bot_gid):
        return False
    last_bot = ""
    last_assign = ""
    for s in stories or []:
        at = s.get("created_at") or ""
        who = (s.get("created_by") or {}).get("gid")
        if who == bot_gid and s.get("resource_subtype") == "comment_added":
            last_bot = max(last_bot, at)
        elif who in trigger_users and s.get("resource_subtype") == "assigned":
            last_assign = max(last_assign, at)
    if not last_assign and (task.get("created_by") or {}).get("gid") in trigger_users:
        last_assign = task.get("created_at") or ""
    return bool(last_assign) and last_assign > last_bot and last_assign > (since or "")


def inbox_wakes(task: dict, stories: list, trigger_users: set, bot_gid: str,
                since: str = "") -> bool:
    """An inbox poll wakes the bot on an open bot task with an unanswered comment
    from Mark or PmBot, or one newly assigned to it. `since` is the task's
    last_wake, so a task already handled is not woken twice."""
    if not task_is_for_bot(task, bot_gid):
        return False
    return (unanswered(stories, trigger_users, bot_gid, since)
            or newly_assigned(task, stories, trigger_users, bot_gid, since))


def home_prefix(task: dict, prefix_of_gid: dict, skip: set = frozenset()) -> str:
    """The registered project a task belongs to, by its memberships. A task
    multi-homed into a queue (SL) is worked in its home project, so queues in
    `skip` never win. Empty when no registered project holds it."""
    for m in task.get("memberships") or []:
        prefix = prefix_of_gid.get(((m or {}).get("project") or {}).get("gid"))
        if prefix and prefix not in skip:
            return prefix
    return ""


def inbox_cursor(last_poll: str, now_iso: str, overlap_s: int, first_s: int) -> str:
    """Lower bound for `modified_at.after`. Search results lag behind writes, so
    each poll reaches back `overlap_s` before the previous one; the first poll
    reaches back `first_s`. ISO-8601 UTC strings in, one out."""
    import datetime as _dt
    now = _dt.datetime.strptime(now_iso, "%Y-%m-%dT%H:%M:%SZ")
    if last_poll:
        start = _dt.datetime.strptime(last_poll, "%Y-%m-%dT%H:%M:%SZ") - _dt.timedelta(seconds=overlap_s)
    else:
        start = now - _dt.timedelta(seconds=first_s)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Sandboxed execution (BSTD-896, ADR 025)
# ---------------------------------------------------------------------------
#
# Claude Code's Bash sandbox (bubblewrap on Linux) confines what a command can
# touch at the OS level, so a script the run writes is held to the same limits
# as the run itself. The permission rules alone cannot do that: they match the
# command string, so `Bash(python3 *)` would let `python3 x.py` read studio/.env.
#
# Verified on Claude Code 2.1.328, 2026-11-19:
#   - It needs bwrap AND socat. Without socat Claude Code warns and runs every
#     command UNSANDBOXED, even with allowUnsandboxedCommands false. Only
#     failIfUnavailable makes it refuse to start instead.
#   - Permission Read() denies are not enforced inside the sandbox: they must be
#     repeated as sandbox.filesystem.denyRead.
#   - --add-dir folders are writable inside it: they must be repeated as
#     sandbox.filesystem.denyWrite.
#   - git cannot commit from inside it (the worktree's git dir is in the main
#     checkout, which is read-only), and sync.py needs .env and Asana. Both run
#     outside it via excludedCommands, still held to the narrow allow rules.

SANDBOX_DEPS = ("bwrap", "socat")

# Commands that are already allowed by run_allow_rules and must run outside the
# sandbox to work. An exclusion does not allow anything by itself.
SANDBOX_EXCLUDED_GIT = ["git status", "git status *", "git diff", "git diff *",
                        "git log", "git log *", "git show *", "git add *", "git commit *"]

# Credentials a script must never read, wherever the run's file rules point.
HOME_SECRETS = (".ssh", ".gnupg", ".aws", ".netrc", ".git-credentials",
                ".claude/.credentials.json", ".config/gh", ".local/share/keyrings")


SECRET_ENV_RE = re.compile(r"(PAT|TOKEN|KEY|PASSWORD|SECRET|CREDENTIALS?|WEBHOOK_URL|SA_JSON)$",
                           re.IGNORECASE)


def strip_env(env: dict, keys) -> dict:
    """`env` without `keys`, and without anything named like a credential in
    case a key reached the listener some other way. The run must not inherit
    the listener's secrets."""
    drop = set(keys)
    return {k: v for k, v in env.items() if k not in drop and not SECRET_ENV_RE.search(k)}


def sandbox_missing(which) -> list:
    """The sandbox dependencies not on PATH. `which` is shutil.which, injected
    so this stays testable. Empty means the sandbox can start."""
    return [d for d in SANDBOX_DEPS if not which(d)]


def bot_test_command(claude_md: str) -> str:
    """The project's own test command, from a `BOT_TEST_COMMAND:` line in its
    CLAUDE.md (same convention as DROPBOX_FOLDER). "" when there is none."""
    m = re.search(r"^BOT_TEST_COMMAND:\s*(\S.*?)\s*$", claude_md or "", re.MULTILINE)
    return m.group(1) if m else ""


def exec_allow_rules(test_command: str = "") -> list:
    """What a sandboxed run may execute, on top of run_allow_rules. Only used
    when the sandbox is up: inside it these reach no network, no credentials and
    no file outside the worktree."""
    rules = ["Bash(python3 *)", "Bash(python3 -m pytest)", "Bash(pytest)", "Bash(pytest *)"]
    if test_command:
        rules += [f"Bash({test_command})", f"Bash({test_command} *)"]
    return rules


def _secret_globs(d: str) -> list:
    out = []
    for name in SECRET_FILES:
        out += [f"{d}/{name}", f"{d}/**/{name}"]
    return out


def protected_writes(roots: list) -> list:
    """The protected_path_denies() files as sandbox write denies. Permission
    rules do not bind a script, and the sandbox does not cover .envrc itself."""
    out = []
    for r in roots:
        if r:
            b = str(r).rstrip("/")
            out += [f"{b}/.git", f"{b}/.claude", f"{b}/.envrc"]
    return out


def sandbox_settings(roots: list, read_only: list, home: Path, sync_py: Path,
                     extra_secrets: list = ()) -> dict:
    """The --settings JSON that turns the sandbox on for one run.

    roots: the project checkout and the run's worktree (secret files denied).
    read_only: --add-dir folders (secret files denied, and no writes).
    extra_secrets: further paths to hide whole, e.g. the listener's state dir
    and a per-project CLAUDE_CONFIG_DIR's credentials.
    Writes are otherwise limited by the sandbox to the working directory.
    """
    deny_read = []
    for d in [*roots, *read_only]:
        if d:
            deny_read += _secret_globs(str(d).rstrip("/"))
    deny_read += [str(home / s) for s in HOME_SECRETS]
    deny_read += [str(p) for p in extra_secrets if p]
    return {"sandbox": {
        "enabled": True,
        "failIfUnavailable": True,
        "autoAllowBashIfSandboxed": False,
        "allowUnsandboxedCommands": False,
        "network": {"allowedDomains": []},
        "excludedCommands": [*SANDBOX_EXCLUDED_GIT,
                             f"python3 {sync_py} --get-task *",
                             f"python3 {sync_py} --comment *"],
        "filesystem": {"denyRead": deny_read,
                       "denyWrite": [*[str(d).rstrip("/") for d in read_only if d],
                                     *protected_writes(roots)]},
    }}

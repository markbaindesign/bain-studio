"""
Studio Asana sync — full bidirectional sync across all active studio projects.

Syncs each project's Asana tasks to <project>/.claude/asana-mirror.md.

Conflict resolution: mirror file mtime vs Asana task modified_at.
- asana_modified_at > mirror_mtime → Asana wins, pull all fields into mirror
- otherwise → mirror wins, push changed fields to Asana

Required env vars (set in studio/.env):
    ASANA_PAT                 Personal access token
    ASANA_WORKSPACE_GID       Workspace GID
    ASANA_BAINBOT_GID         GID of the Asana user tasks are assigned to
    ASANA_LOCAL_ID_FIELD_GID  GID of the custom text field used for local IDs

Projects registry: studio/projects.json (gitignored — copy from projects.example.json)

Usage:
    python sync.py                                          # sync all discovered projects
    python sync.py --project MCF                            # sync one project by prefix
    python sync.py --dry-run                                # preview only, no writes or Asana mutations
    python sync.py --create --name "Client" --prefix CLI --path /path/to/project
                                                            # scaffold a new project from template

Log: studio/sync.log (rotating, 5 MB × 3)
"""

import argparse
import logging
import os
import re
import sys
import json
import time
import requests
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

STUDIO_DIR = Path(__file__).parent
load_dotenv(STUDIO_DIR / ".env")

ASANA_PAT            = os.getenv("ASANA_PAT") or os.getenv("ASANA_TOKEN")
WORKSPACE_GID        = os.getenv("ASANA_WORKSPACE_GID")
BAINBOT_GID          = os.getenv("ASANA_BAINBOT_GID")
ASSIGNEE_NAME        = os.getenv("STUDIO_ASSIGNEE_NAME", "Bot")
TEMPLATE_PROJECT_GID = os.getenv("ASANA_TEMPLATE_PROJECT_GID")
USER_GID             = os.getenv("ASANA_USER_GID")
TODAY          = date.today().isoformat()
BASE_URL       = "https://app.asana.com/api/1.0"

SKIP_PREFIXES  = set()

JUNK_PATTERNS  = re.compile(r"^- |😍|📰|\[Product Update\]", re.IGNORECASE)
PLAIN_CHECK    = re.compile(r"^Checked \d{4}-\d{2}-\d{2}\.$")
GID_IN_PARENS  = re.compile(r'\((\d+)\)')
FIELD_RE       = re.compile(r"- \*\*(.+?):\*\* (.+)")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("sync")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    fh = RotatingFileHandler(
        STUDIO_DIR / "sync.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    return logger

log = _setup_logging()


# ---------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------

@dataclass
class ProjectConfig:
    name:   str
    root:   Path
    gid:    str
    prefix: str

    @property
    def mirror_file(self): return self.root / ".claude" / "asana-mirror.md"

    @property
    def ids_file(self): return self.root / ".claude" / "asana-ids.json"

    @property
    def claude_dir(self): return self.root / ".claude"


PROJECTS_FILE = STUDIO_DIR / "projects.json"


def load_projects_registry() -> list:
    """Load projects.json, migrating flat path arrays to object format."""
    if not PROJECTS_FILE.exists():
        return []
    try:
        data = json.loads(PROJECTS_FILE.read_text())
    except Exception as e:
        log.error(f"Could not parse {PROJECTS_FILE}: {e}")
        return []
    # Migrate flat list of strings → list of {path, status} objects
    migrated = False
    result = []
    for entry in data:
        if isinstance(entry, str):
            result.append({"path": entry, "status": "active"})
            migrated = True
        else:
            result.append(entry)
    if migrated:
        PROJECTS_FILE.write_text(json.dumps(result, indent=2) + "\n")
        log.info("projects.json migrated to object format")
    return result


def discover_projects(filter_prefix=None) -> list:
    registry = load_projects_registry()
    if not registry:
        log.error(f"No projects.json found at {PROJECTS_FILE}. Copy projects.example.json to get started.")
        return []

    projects = []
    seen_gids = set()

    for entry in registry:
        raw    = entry["path"]
        status = entry.get("status", "active")
        # Skip paused and archived projects unless explicitly filtered by prefix
        if status in ("paused", "archived") and not filter_prefix:
            continue
        root = Path(raw).expanduser()
        claude_md = root / "CLAUDE.md"
        if not claude_md.exists():
            log.warning(f"  Skipping {raw} — no CLAUDE.md found")
            continue

        try:
            text = claude_md.read_text(errors="replace")
        except OSError as e:
            log.warning(f"  Skipping {raw} — could not read CLAUDE.md: {e}")
            continue

        gid_m    = re.search(r"ASANA_PROJECT_GID:\s*(\S+)", text)
        prefix_m = re.search(r"ASANA_TASK_PREFIX:\s*(\S+)", text)
        if not gid_m:
            log.warning(f"  Skipping {raw} — no ASANA_PROJECT_GID in CLAUDE.md")
            continue

        gid    = gid_m.group(1)
        prefix = prefix_m.group(1) if prefix_m else root.name.upper()[:4]

        if gid in seen_gids or prefix in SKIP_PREFIXES:
            continue
        if filter_prefix and prefix != filter_prefix:
            continue

        name_m = re.search(r"ASANA_PROJECT_NAME:\s*(.+)", text)
        name   = name_m.group(1).strip() if name_m else (
            root.name.replace("_", " ").replace("-", " ").title()
        )

        projects.append(ProjectConfig(name=name, root=root, gid=gid, prefix=prefix))
        seen_gids.add(gid)

    return projects


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _h():
    return {"Authorization": f"Bearer {ASANA_PAT}", "Accept": "application/json"}

def _get(path, params=None):
    r = requests.get(f"{BASE_URL}{path}", headers=_h(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def _post(path, payload):
    r = requests.post(f"{BASE_URL}{path}", headers=_h(), json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def _put(path, payload):
    r = requests.put(f"{BASE_URL}{path}", headers=_h(), json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def _delete(path):
    r = requests.delete(f"{BASE_URL}{path}", headers=_h(), timeout=15)
    r.raise_for_status()

def _wait_for_job(job_gid, interval=5, timeout=300):
    """Poll GET /jobs/{job_gid} until succeeded. Returns the new_project dict."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = _get(f"/jobs/{job_gid}")
        status = result["data"]["status"]
        if status == "succeeded":
            return result["data"]["new_project"]
        if status == "failed":
            raise RuntimeError(f"Asana job {job_gid} failed")
        time.sleep(interval)
    raise TimeoutError(f"Asana job {job_gid} timed out after {timeout}s")


# ---------------------------------------------------------------------------
# Local ID state
# ---------------------------------------------------------------------------

def load_ids(proj: ProjectConfig) -> dict:
    if proj.ids_file.exists():
        data = json.loads(proj.ids_file.read_text())
        data.setdefault("last_synced_field_gid", None)
        return data
    return {"custom_field_gid": None, "last_synced_field_gid": None, "tasks": {}, "next_seq": 1, "posted_progress": {}}


def save_ids(proj: ProjectConfig, state: dict, dry_run=False):
    if dry_run:
        return
    proj.claude_dir.mkdir(exist_ok=True)
    proj.ids_file.write_text(json.dumps(state, indent=2))


def _next_lid(state: dict, prefix: str) -> str:
    lid = f"{prefix}-{state['next_seq']:03d}"
    state["next_seq"] += 1
    return lid


# ---------------------------------------------------------------------------
# Custom field
# ---------------------------------------------------------------------------

SHARED_FIELD_GID       = os.getenv("ASANA_LOCAL_ID_FIELD_GID", "")
LAST_SYNCED_FIELD_GID  = os.getenv("ASANA_LAST_SYNCED_FIELD_GID", "")


def _create_and_attach_field(proj: ProjectConfig, field_name: str, env_var: str) -> str:
    log.info(f"  Creating '{field_name}' custom field in workspace...")
    resp = _post("/custom_fields", {"data": {
        "name": field_name,
        "resource_subtype": "text",
        "workspace": WORKSPACE_GID,
    }})
    field_gid = resp["data"]["gid"]
    log.info(f"  Created {field_gid} — add {env_var}={field_gid} to .env to reuse across projects")
    try:
        _post(f"/projects/{proj.gid}/addCustomFieldSetting", {"data": {
            "custom_field": field_gid, "is_important": True,
        }})
    except Exception as e:
        err = str(e).lower()
        if "already" not in err and "403" not in err and "forbidden" not in err:
            log.warning(f"  Could not attach '{field_name}' field: {e}")
    return field_gid


def setup_project_fields(proj: ProjectConfig, dry_run=False):
    log.info(f"\n[{proj.prefix}] {proj.name} — field setup")
    log.info(f"  Path: {proj.root}")
    state = load_ids(proj)
    proj.claude_dir.mkdir(exist_ok=True)

    fields = [
        ("custom_field_gid",      "Local ID",    SHARED_FIELD_GID,       "ASANA_LOCAL_ID_FIELD_GID"),
        ("last_synced_field_gid", "Last Synced", LAST_SYNCED_FIELD_GID,  "ASANA_LAST_SYNCED_FIELD_GID"),
    ]
    for state_key, name, env_gid, env_var in fields:
        if state.get(state_key):
            log.info(f"  {name}: already set ({state[state_key]})")
            continue
        if dry_run:
            log.info(f"  [DRY-RUN] Would create/attach '{name}' field")
            continue
        if env_gid:
            log.info(f"  {name}: attaching from env ({env_gid})...")
            try:
                _post(f"/projects/{proj.gid}/addCustomFieldSetting", {"data": {
                    "custom_field": env_gid, "is_important": True,
                }})
                log.info(f"  {name}: attached {env_gid}")
            except Exception as e:
                err = str(e).lower()
                if "already" in err or "403" in err or "forbidden" in err:
                    log.info(f"  {name}: {env_gid} already attached")
                else:
                    log.warning(f"  {name}: could not attach {env_gid}: {e}")
            state[state_key] = env_gid
        else:
            state[state_key] = _create_and_attach_field(proj, name, env_var)

    save_ids(proj, state, dry_run)
    if not dry_run:
        log.info(f"  Saved → {proj.ids_file}")


def ensure_custom_field(proj: ProjectConfig, state: dict, dry_run=False) -> str:
    gid = state.get("custom_field_gid") or ""
    if not gid and not dry_run:
        log.warning(f"  [{proj.prefix}] Local ID field not configured — run: python3 sync.py --setup --project {proj.prefix}")
    return gid


def ensure_last_synced_field(proj: ProjectConfig, state: dict) -> str:
    gid = state.get("last_synced_field_gid") or ""
    if not gid:
        log.warning(f"  [{proj.prefix}] Last Synced field not configured — run: python3 sync.py --setup --project {proj.prefix}")
    return gid


# ---------------------------------------------------------------------------
# Task fetching
# ---------------------------------------------------------------------------

def fetch_tasks(proj: ProjectConfig, field_gid: str) -> list:
    log.info(f"  [{proj.prefix}] Fetching tasks from Asana...")
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
    params = {
        "completed_since": thirty_days_ago,
        "opt_fields": (
            "gid,name,notes,due_on,due_at,start_on,completed,modified_at,permalink_url,"
            "assignee.gid,assignee.name,assignee_status,"
            "custom_fields.gid,custom_fields.text_value,"
            "memberships.section.name,memberships.section.gid,memberships.project.gid,"
            "tags.gid,tags.name,"
            "followers.gid,followers.name,"
            "dependencies.gid,dependencies.name,"
            "dependents.gid,dependents.name"
        ),
        "limit": 100,
    }
    data = _get(f"/projects/{proj.gid}/tasks", params)["data"]
    tasks = [t for t in data
             if (t.get("assignee") or {}).get("gid") == BAINBOT_GID
             and not _is_junk(t)]
    for t in tasks:
        t["_local_id"] = None
        t["_section"]  = None
        t["_section_gid"] = None
        for cf in t.get("custom_fields", []):
            if cf.get("gid") == field_gid:
                t["_local_id"] = cf.get("text_value") or None
                break
        for m in t.get("memberships", []):
            if (m.get("project") or {}).get("gid") == proj.gid:
                sec = m.get("section") or {}
                t["_section"]     = sec.get("name")
                t["_section_gid"] = sec.get("gid")
                break
    return tasks


def fetch_sections(proj: ProjectConfig) -> dict:
    data = _get(f"/projects/{proj.gid}/sections")["data"]
    return {s["name"]: s["gid"] for s in data}


def fetch_comments(task_gid: str) -> list:
    """Return human-written comments on a task, excluding bainbot's own progress notes."""
    try:
        data = _get(f"/tasks/{task_gid}/stories", {
            "opt_fields": "created_at,created_by.gid,created_by.name,text,resource_subtype",
            "limit": 50,
        })["data"]
    except Exception:
        return []
    comments = []
    for s in data:
        if s.get("resource_subtype") != "comment_added":
            continue
        creator = s.get("created_by") or {}
        if creator.get("gid") == BAINBOT_GID:
            continue
        text = (s.get("text") or "").strip()
        if not text:
            continue
        created = (s.get("created_at") or "")[:10]
        author = creator.get("name", "Unknown")
        comments.append({"author": author, "text": text, "created_at": created})
    return comments


def _is_junk(task) -> bool:
    name = task.get("name", "")
    projects = task.get("projects", [])
    if not projects and JUNK_PATTERNS.search(name):
        return True
    if len(name) > 120 and not projects:
        return True
    return False


# ---------------------------------------------------------------------------
# ID assignment
# ---------------------------------------------------------------------------

def assign_ids(proj: ProjectConfig, tasks: list, state: dict, field_gid: str, dry_run=False) -> dict:
    assigned = 0
    for t in tasks:
        gid = t["gid"]
        if t["_local_id"]:
            if gid not in state["tasks"]:
                state["tasks"][gid] = t["_local_id"]
            continue
        lid = state["tasks"].get(gid) or _next_lid(state, proj.prefix)
        state["tasks"][gid] = lid
        t["_local_id"] = lid
        if not dry_run:
            try:
                _put(f"/tasks/{gid}", {"data": {"custom_fields": {field_gid: lid}}})
                assigned += 1
            except Exception as e:
                log.warning(f"  [{proj.prefix}] Note: could not write Local ID to Asana ({gid}): {e}")
    save_ids(proj, state, dry_run)
    if assigned:
        log.info(f"  [{proj.prefix}] Assigned {assigned} new Local ID(s).")
    return state


# ---------------------------------------------------------------------------
# Last Synced stamping
# ---------------------------------------------------------------------------

def stamp_last_synced(proj: ProjectConfig, tasks: list, field_gid: str, dry_run=False):
    if not field_gid or dry_run:
        return
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    for t in tasks:
        try:
            _put(f"/tasks/{t['gid']}", {"data": {"custom_fields": {field_gid: now}}})
        except Exception as e:
            log.warning(f"  [{proj.prefix}] Could not stamp Last Synced on {t['gid']}: {e}")


# ---------------------------------------------------------------------------
# Reference formatting helpers
# ---------------------------------------------------------------------------

def _fmt_refs(items: list) -> str:
    if not items:
        return "none"
    return ", ".join(f"{i['name']} ({i['gid']})" for i in items)


def _fmt_task_refs(items: list, gid_to_lid: dict) -> str:
    if not items:
        return "none"
    parts = []
    for i in items:
        gid   = i["gid"]
        label = gid_to_lid.get(gid) or i.get("name") or gid
        parts.append(f"{label} ({gid})")
    return ", ".join(parts)


def _extract_gids(text: str) -> list:
    return GID_IN_PARENS.findall(text) if text and text != "none" else []


# ---------------------------------------------------------------------------
# Mirror parsing
# ---------------------------------------------------------------------------

def parse_existing_mirror(proj: ProjectConfig) -> dict:
    if not proj.mirror_file.exists():
        return {}
    carried = {}
    text   = proj.mirror_file.read_text()
    blocks = re.split(r"\n(?=### )", text)
    for block in blocks:
        if not block.startswith("### "):
            continue
        fields = {}
        for m in FIELD_RE.finditer(block):
            key = m.group(1).lower().replace(" ", "_")
            fields[key] = m.group(2).strip()
        gid = fields.get("asana_id")
        if not gid:
            continue
        due = (fields.get("due") or "none").replace(" **(OVERDUE)**", "").strip()
        carried[gid] = {
            "local_id":        fields.get("local_id", "—"),
            "section":         fields.get("section") or None,
            "due":             due,
            "start":           fields.get("start", "none"),
            "notes":           fields.get("notes", ""),
            "assignee":        fields.get("assignee", "none"),
            "assignee_status": fields.get("assignee_status", "none"),
            "tags":            fields.get("tags", "none"),
            "followers":       fields.get("followers", "none"),
            "dependencies":    fields.get("dependencies", "none"),
            "dependents":      fields.get("dependents", "none"),
            "blockers":        fields.get("blockers", "None identified."),
            "progress":        fields.get("progress", ""),
            "modified":        fields.get("modified", ""),
        }
    return carried


def parse_existing_task_gids(proj: ProjectConfig) -> set:
    if not proj.mirror_file.exists():
        return set()
    return set(re.findall(r"- \*\*Asana ID:\*\* (\d+)", proj.mirror_file.read_text()))


# ---------------------------------------------------------------------------
# Mirror building
# ---------------------------------------------------------------------------

def _task_lines(t: dict, carried: dict, gid_to_lid: dict) -> list:
    gid      = t["gid"]
    prev     = carried.get(gid, {})
    local_id = t.get("_local_id") or prev.get("local_id") or "—"
    section  = t.get("_section") or prev.get("section") or "—"

    blockers = prev.get("blockers") or "None identified."
    prev_p   = prev.get("progress", "")
    progress = f"Checked {TODAY}." if (not prev_p or PLAIN_CHECK.match(prev_p)) else prev_p

    due      = t.get("due_on") or "none"
    overdue  = " **(OVERDUE)**" if due != "none" and due < TODAY else ""
    start    = t.get("start_on") or "none"
    notes    = (t.get("notes") or "").strip() or "No notes."
    modified = (t.get("modified_at") or "")[:19]

    assignee     = t.get("assignee") or {}
    assignee_str = f"{assignee['name']} ({assignee['gid']})" if assignee.get("gid") else "none"
    astat        = t.get("assignee_status") or "none"

    tags       = _fmt_refs(t.get("tags", []))
    followers  = _fmt_refs(t.get("followers", []))
    deps       = _fmt_task_refs(t.get("dependencies", []), gid_to_lid)
    dependents = _fmt_task_refs(t.get("dependents", []), gid_to_lid)

    raw_comments = t.get("_comments") or []
    if raw_comments:
        comment_lines = ["- **Comments:**"]
        for c in raw_comments:
            text = c["text"].replace("\n", " ").strip()
            comment_lines.append(f"  > {c['created_at']} **{c['author']}:** {text}")
    else:
        comment_lines = ["- **Comments:** none"]

    return [
        f"### {local_id} — {t['name']}",
        f"- **Local ID:** {local_id}",
        f"- **Asana ID:** {gid}",
        f"- **Section:** {section}",
        f"- **Due:** {due}{overdue}",
        f"- **Start:** {start}",
        f"- **Assignee:** {assignee_str}",
        f"- **Assignee Status:** {astat}",
        f"- **Tags:** {tags}",
        f"- **Followers:** {followers}",
        f"- **Dependencies:** {deps}",
        f"- **Dependents:** {dependents}",
        f"- **Notes:** {notes}",
        f"- **Blockers:** {blockers}",
        f"- **Progress:** {progress}",
        *comment_lines,
        f"- **Modified:** {modified}",
        f"- **URL:** {t.get('permalink_url', '')}",
        "",
    ]


def build_mirror(proj: ProjectConfig, tasks: list, carried: dict, gid_to_lid: dict) -> str:
    active = [t for t in tasks if not t.get("completed")]
    done   = sorted([t for t in tasks if t.get("completed")],
                    key=lambda t: t.get("modified_at", ""), reverse=True)

    lines = [
        f"# {ASSIGNEE_NAME} Asana Task Mirror",
        f"Last synced: {TODAY}",
        f"Workspace GID: {WORKSPACE_GID}",
        f"Assignee GID: {BAINBOT_GID}",
        "",
        f"## {proj.name}",
        "",
    ]
    for t in active:
        lines += _task_lines(t, carried, gid_to_lid)

    if done:
        lines += ["", "## DONE", ""]
        for t in done:
            lines += _task_lines(t, carried, gid_to_lid)

    return "\n".join(lines)


def priorities_table(tasks: list) -> str:
    active   = [t for t in tasks if not t.get("completed")]
    week_out = (date.today() + timedelta(days=7)).isoformat()
    overdue  = [t for t in active if t.get("due_on") and t["due_on"] < TODAY]
    due_soon = [t for t in active if t.get("due_on") and TODAY <= t["due_on"] <= week_out]
    no_due   = [t for t in active if not t.get("due_on")]

    rows = []
    for t in overdue:
        rows.append(f"| {t.get('_local_id','?')} | {t['name'][:50]} | {t['due_on']} OVERDUE |")
    for t in due_soon:
        rows.append(f"| {t.get('_local_id','?')} | {t['name'][:50]} | due {t['due_on']} |")
    for t in no_due[:5]:
        rows.append(f"| {t.get('_local_id','?')} | {t['name'][:50]} | no due date |")

    if not rows:
        return ""
    table = ["", "## Immediate Priorities", "", "| ID | Task | Status |", "|----|------|--------|"]
    table += rows
    return "\n".join(table)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def leave_comment(task_gid: str, text: str, dry_run=False):
    if dry_run:
        log.info(f"    [DRY-RUN] Would comment on {task_gid}: {text[:80]}...")
        return
    _post(f"/tasks/{task_gid}/stories", {"data": {"text": text}})


# ---------------------------------------------------------------------------
# Push helpers
# ---------------------------------------------------------------------------

def _push_simple_fields(t: dict, prev: dict, dry_run: bool, prefix: str) -> bool:
    gid     = t["gid"]
    lid     = t.get("_local_id", gid)
    updates = {}

    def _diff(mirror_val, asana_val):
        return (mirror_val or "").strip() != (asana_val or "").strip()

    # Notes are read-only in the mirror — multi-line content doesn't survive the
    # FIELD_RE single-line parser, so pushing notes would silently truncate them.
    # Edit notes directly in Asana.

    due = prev.get("due", "none")
    if _diff(due, t.get("due_on") or "none"):
        updates["due_on"] = due if due != "none" else None

    start = prev.get("start", "none")
    if _diff(start, t.get("start_on") or "none"):
        updates["start_on"] = start if start != "none" else None

    astat = prev.get("assignee_status", "none")
    if _diff(astat, t.get("assignee_status") or "none") and astat != "none":
        updates["assignee_status"] = astat

    if not updates:
        return False
    if dry_run:
        log.info(f"    [DRY-RUN] Would PUT {lid}: {list(updates.keys())}")
        return False
    try:
        _put(f"/tasks/{gid}", {"data": updates})
        log.info(f"  [{prefix}] Pushed to {lid}: {list(updates.keys())}")
        return True
    except Exception as e:
        log.warning(f"  [{prefix}] Could not push fields to {lid}: {e}")
        return False


def _push_set_field(task_gid: str, lid: str, mirror_text: str, asana_items: list,
                    add_path: str, remove_path: str, item_key: str,
                    dry_run: bool, prefix: str, label: str) -> bool:
    mirror_gids = set(_extract_gids(mirror_text))
    asana_gids  = {i["gid"] for i in (asana_items or [])}
    to_add    = mirror_gids - asana_gids
    to_remove = asana_gids - mirror_gids
    if not to_add and not to_remove:
        return False
    if dry_run:
        log.info(f"    [DRY-RUN] Would update {label} for {lid}: +{to_add} -{to_remove}")
        return False
    changed = False
    for g in to_add:
        try:
            _post(add_path.format(task_gid=task_gid), {"data": {item_key: g}})
            changed = True
        except Exception as e:
            log.warning(f"  [{prefix}] Could not add {label} {g} to {lid}: {e}")
    for g in to_remove:
        try:
            _post(remove_path.format(task_gid=task_gid), {"data": {item_key: g}})
            changed = True
        except Exception as e:
            log.warning(f"  [{prefix}] Could not remove {label} {g} from {lid}: {e}")
    if changed:
        log.info(f"  [{prefix}] Updated {label} for {lid} (+{len(to_add)}/-{len(to_remove)})")
    return changed


def _push_section(t: dict, mirror_section: str, sections: dict, dry_run: bool, prefix: str) -> bool:
    gid        = t["gid"]
    lid        = t.get("_local_id", gid)
    target_gid = sections.get(mirror_section)
    if not target_gid:
        log.warning(f"  [{prefix}] Unknown section '{mirror_section}' for {lid} — skipping")
        return False
    if dry_run:
        log.info(f"    [DRY-RUN] Would move {lid} → '{mirror_section}'")
        return False
    try:
        _post(f"/sections/{target_gid}/addTask", {"data": {"task": gid}})
        log.info(f"  [{prefix}] Moved {lid}: '{t.get('_section')}' → '{mirror_section}'")
        t["_section"] = mirror_section
    except Exception as e:
        log.warning(f"  [{prefix}] Could not move {lid}: {e}")
        return False
    was_done = t.get("completed", False)
    now_done = mirror_section == "DONE"
    if now_done != was_done:
        try:
            _put(f"/tasks/{gid}", {"data": {"completed": now_done}})
            t["completed"] = now_done
        except Exception as e:
            log.warning(f"  [{prefix}] Could not set completed={now_done} on {lid}: {e}")
    return True


# ---------------------------------------------------------------------------
# Per-project sync
# ---------------------------------------------------------------------------

def sync_project(proj: ProjectConfig, dry_run=False) -> bool:
    log.info(f"\n[{proj.prefix}] {proj.name}")
    log.info(f"  Path: {proj.root}")
    log.info(f"  GID:  {proj.gid}")
    try:
        proj.claude_dir.mkdir(exist_ok=True)

        state           = load_ids(proj)
        field_gid       = ensure_custom_field(proj, state, dry_run)
        last_synced_gid = ensure_last_synced_field(proj, state)

        tasks = fetch_tasks(proj, field_gid)
        log.info(f"  {len(tasks)} task(s) assigned to {ASSIGNEE_NAME}.")
        for t in tasks:
            t["_comments"] = fetch_comments(t["gid"])

        prev_gids    = parse_existing_task_gids(proj)
        curr_gids    = {t["gid"] for t in tasks}
        new_gids     = curr_gids - prev_gids
        removed_gids = prev_gids - curr_gids

        carried  = parse_existing_mirror(proj)
        sections = fetch_sections(proj)
        log.info(f"  [{proj.prefix}] Sections: {list(sections.keys())}")

        state      = assign_ids(proj, tasks, state, field_gid, dry_run)
        gid_to_lid = state.get("tasks", {})
        stamp_last_synced(proj, tasks, last_synced_gid, dry_run)

        # Per-task last-sync timestamps — used for conflict resolution.
        # Comparing against mirror file mtime was wrong: sync.py rewrites the
        # mirror every run, so mirror_mtime was always "now", causing any Asana
        # change made after the last run to be overwritten by the local mirror.
        last_sync_times = state.get("last_sync_times", {})
        now_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

        # --- Bidirectional field sync ---
        pushed = 0
        for t in tasks:
            gid  = t["gid"]
            prev = carried.get(gid)
            if not prev:
                last_sync_times[gid] = now_utc
                continue  # new task — nothing in mirror to push

            asana_mod = (t.get("modified_at") or "")[:19]
            task_last_sync = last_sync_times.get(gid, "")

            if asana_mod > task_last_sync:
                # Asana is newer — pull (mirror rebuilds from t fields naturally)
                last_sync_times[gid] = now_utc
                continue

            # Mirror is newer — push all changed fields to Asana
            lid = t.get("_local_id", gid)

            if _push_simple_fields(t, prev, dry_run, proj.prefix):
                pushed += 1

            for label, mirror_key, asana_key, add_path, remove_path, item_key in [
                ("tags",         "tags",         "tags",         "/tasks/{task_gid}/addTag",          "/tasks/{task_gid}/removeTag",          "tag"),
                ("followers",    "followers",    "followers",    "/tasks/{task_gid}/addFollowers",     "/tasks/{task_gid}/removeFollowers",     "followers"),
                ("dependencies", "dependencies", "dependencies", "/tasks/{task_gid}/addDependencies",  "/tasks/{task_gid}/removeDependencies",  "dependencies"),
                ("dependents",   "dependents",   "dependents",   "/tasks/{task_gid}/addDependents",    "/tasks/{task_gid}/removeDependents",    "dependents"),
            ]:
                if _push_set_field(
                    gid, lid,
                    prev.get(mirror_key), t.get(asana_key, []),
                    add_path, remove_path, item_key,
                    dry_run, proj.prefix, label,
                ):
                    pushed += 1

            mirror_section = prev.get("section")
            if mirror_section and mirror_section != t.get("_section"):
                if _push_section(t, mirror_section, sections, dry_run, proj.prefix):
                    pushed += 1

            last_sync_times[gid] = now_utc

        state["last_sync_times"] = last_sync_times

        # --- Progress comments ---
        posted_progress = state.get("posted_progress", {})
        commented = 0

        # Guard: if the same non-trivial progress text appears on more than 2 tasks,
        # it was almost certainly written by a replace_all bug in the mirror editor.
        # Skip the batch rather than spam every task with the same comment.
        progress_texts = [
            (prev or {}).get("progress", "")
            for t in tasks
            for prev in [carried.get(t["gid"])]
            if (prev or {}).get("progress", "") and not PLAIN_CHECK.match((prev or {}).get("progress", ""))
        ]
        from collections import Counter
        progress_counts = Counter(progress_texts)

        for t in tasks:
            gid      = t["gid"]
            prev     = carried.get(gid)
            curr_p   = (prev or {}).get("progress", "")
            local_id = t.get("_local_id", "?")

            if (curr_p
                    and not PLAIN_CHECK.match(curr_p)
                    and curr_p != posted_progress.get(gid)):
                if progress_counts[curr_p] > 2:
                    log.warning(f"  [{proj.prefix}] Skipping comment for {local_id} — same progress text on {progress_counts[curr_p]} tasks (mirror edit bug?)")
                    continue
                try:
                    log.info(f"  [{proj.prefix}] Posting progress comment for {local_id}...")
                    leave_comment(gid, curr_p, dry_run)
                    if not dry_run:
                        posted_progress[gid] = curr_p
                    commented += 1
                except Exception as e:
                    log.warning(f"  Failed to comment on {local_id}: {e}")

        state["posted_progress"] = posted_progress
        save_ids(proj, state, dry_run)

        mirror = build_mirror(proj, tasks, carried, gid_to_lid)

        if new_gids or removed_gids:
            changes = ["\n## Changes This Sync\n"]
            for gid in new_gids:
                t = next(x for x in tasks if x["gid"] == gid)
                changes.append(f"- NEW: {t.get('_local_id','?')} — {t['name']}")
            for gid in removed_gids:
                lid = state["tasks"].get(gid, gid)
                changes.append(f"- REMOVED (likely completed): {lid}")
            mirror += "\n" + "\n".join(changes)

        mirror += priorities_table(tasks)

        if not dry_run:
            proj.mirror_file.write_text(mirror)
            log.info(f"  Mirror → {proj.mirror_file}")
        else:
            log.info(f"  [DRY-RUN] Mirror would be written to {proj.mirror_file}")

        log.info(f"  {len(new_gids)} new | {len(removed_gids)} removed | {commented} comment(s) | {pushed} push(es)")
        return True

    except Exception as e:
        log.error(f"  FAILED: {e}")
        return False


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def write_registry(projects: list, results: dict):
    lines = [
        "# Studio Project Registry",
        f"Last updated: {TODAY}",
        "",
        "| Prefix | Name | Path | Asana GID | Status |",
        "|--------|------|------|-----------|--------|",
    ]
    for p in projects:
        status = "OK" if results.get(p.prefix) else "FAILED"
        lines.append(f"| {p.prefix} | {p.name} | `{p.root}` | {p.gid} | {status} |")
    (STUDIO_DIR / "projects.md").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Task creation (--create-task)
# ---------------------------------------------------------------------------

def create_task(project_gid: str, name: str, notes: str = '', assignee_gid: str = None,
                depends_on_gid: str = None, dry_run: bool = False) -> str:
    """
    Create a task in the given Asana project via bainbot, return the new task GID.
    Optionally set it as a dependency of depends_on_gid.
    """
    payload = {
        "data": {
            "name": name,
            "projects": [project_gid],
            "workspace": WORKSPACE_GID,
        }
    }
    if notes:
        payload["data"]["notes"] = notes
    if assignee_gid:
        payload["data"]["assignee"] = assignee_gid

    if dry_run:
        log.info(f"  [DRY-RUN] Would create task: {name!r}")
        return "dry-run-gid"

    resp = _post("/tasks", payload)
    new_gid = resp["data"]["gid"]
    log.info(f"  Task created: {name!r} ({new_gid})")

    if depends_on_gid:
        _post(f"/tasks/{depends_on_gid}/addDependencies", {"data": {"dependencies": [new_gid]}})
        log.info(f"  Linked as dependency of {depends_on_gid}")

    return new_gid


# ---------------------------------------------------------------------------
# Project scaffold (--create)
# ---------------------------------------------------------------------------

def scaffold_project(name, prefix, path, template_gid, extra_members=None, dry_run=False, yes=False):
    path = Path(path).expanduser().resolve()
    log.info(f"\n=== Creating project: {name} ({prefix}) ===")

    if not template_gid:
        log.error("No template project GID. Set ASANA_TEMPLATE_PROJECT_GID in .env or use --template.")
        sys.exit(1)

    # 1. Duplicate template
    log.info(f"  Duplicating template {template_gid}...")
    if not dry_run:
        resp = _post(f"/projects/{template_gid}/duplicate", {"data": {
            "name": name,
            "include": ["notes"],
        }})
        job_gid = resp["data"]["gid"]
        log.info(f"  Job started: {job_gid} — waiting...")
        project_ref = _wait_for_job(job_gid)
        new_gid = project_ref["gid"]
        log.info(f"  Project created: {new_gid}")
    else:
        log.info(f"  [DRY-RUN] Would duplicate template → '{name}'")
        new_gid = "DRY-RUN-GID"

    # 2. Delete placeholder tasks (with confirmation gate)
    if not dry_run:
        tasks = _get(f"/projects/{new_gid}/tasks", params={"opt_fields": "gid"}).get("data", [])
        if tasks:
            if not yes:
                proj_data = _get(f"/projects/{new_gid}", params={"opt_fields": "name,created_at"}).get("data", {})
                created_at = proj_data.get("created_at", "unknown")[:10]
                print(f"\n  ⚠️  About to delete {len(tasks)} task(s) from:")
                print(f"       Name:    {name}")
                print(f"       GID:     {new_gid}")
                print(f"       Created: {created_at}")
                print(f"       URL:     https://app.asana.com/0/{new_gid}/list")
                confirm = input(f"\n  Type the project GID to confirm deletion: ").strip()
                if confirm != new_gid:
                    log.error("  GID did not match — aborting task deletion. Project was created but tasks were not cleared.")
                    log.error(f"  Re-run with --yes to skip this gate, or clear tasks manually.")
                    sys.exit(1)
            log.info(f"  Deleting {len(tasks)} placeholder task(s)...")
            for task in tasks:
                _delete(f"/tasks/{task['gid']}")
        else:
            log.info("  No placeholder tasks to delete.")
    else:
        log.info("  [DRY-RUN] Would delete placeholder tasks")

    # 3. Add members
    members = [m for m in ([BAINBOT_GID, USER_GID] + (extra_members or [])) if m]
    if not dry_run:
        _post(f"/projects/{new_gid}/addMembers", {"data": {"members": members}})
        log.info(f"  Added {len(members)} member(s)")
    else:
        log.info(f"  [DRY-RUN] Would add members: {members}")

    # 4. Scaffold local directory
    log.info(f"  Scaffolding {path} ...")
    if not dry_run:
        claude_dir = path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        ids_file = claude_dir / "asana-ids.json"
        if not ids_file.exists():
            ids_file.write_text(json.dumps({
                "tasks": {}, "next_seq": 1,
                "last_sync_times": {}, "posted_progress": {},
            }, indent=2) + "\n")

        asana_block = (
            f"\n## Asana\n\n"
            f"ASANA_PROJECT_GID: {new_gid}\n"
            f"ASANA_TASK_PREFIX: {prefix}\n"
            f"ASANA_PROJECT_NAME: {name}\n"
        )
        claude_md = path / "CLAUDE.md"
        if claude_md.exists():
            existing = claude_md.read_text()
            if "ASANA_PROJECT_GID" not in existing:
                claude_md.write_text(existing.rstrip() + "\n" + asana_block)
        else:
            claude_md.write_text(f"# {name}\n{asana_block}")

        registry = load_projects_registry()
        paths_in_registry = [e["path"] for e in registry]
        if str(path) not in paths_in_registry:
            registry.append({"path": str(path), "status": "active"})
            PROJECTS_FILE.write_text(json.dumps(registry, indent=2) + "\n")
            log.info(f"  Registered in {PROJECTS_FILE}")
    else:
        log.info(f"  [DRY-RUN] Would scaffold {path}/.claude/ and update CLAUDE.md + projects.json")

    # 5. Attach custom fields + initial sync
    if not dry_run:
        proj = ProjectConfig(name=name, root=path, gid=new_gid, prefix=prefix)
        setup_project_fields(proj, dry_run=False)
        sync_project(proj, dry_run=False)

    log.info(f"\n=== Done ===")
    log.info(f"  Name:   {name}")
    log.info(f"  Prefix: {prefix}")
    log.info(f"  GID:    {new_gid}")
    log.info(f"  Path:   {path}")
    log.info(f"  URL:    https://app.asana.com/0/{new_gid}/list")
    log.info(f"\n  ⚠️  Set the custom project icon manually in Asana — the API cannot copy it.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Studio Asana sync")
    parser.add_argument("--project", metavar="PREFIX",
                        help="Target a single project by its ASANA_TASK_PREFIX (e.g. MCF)")
    parser.add_argument("--setup", action="store_true",
                        help="Create and attach custom fields, write GIDs to asana-ids.json, then exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discover and preview — no writes to mirrors or Asana")
    parser.add_argument("--create", action="store_true",
                        help="Scaffold a new project from the Asana template")
    parser.add_argument("--name", metavar="NAME",
                        help="Project name (required with --create)")
    parser.add_argument("--prefix", metavar="PREFIX",
                        help="Task ID prefix, e.g. MUR (required with --create)")
    parser.add_argument("--path", metavar="PATH",
                        help="Local project directory (required with --create)")
    parser.add_argument("--template", metavar="GID",
                        help="Override template project GID (default: ASANA_TEMPLATE_PROJECT_GID in .env)")
    parser.add_argument("--members", metavar="GID,GID",
                        help="Extra workspace member GIDs to add, comma-separated")
    parser.add_argument("--yes", action="store_true",
                        help="Skip the task-deletion confirmation gate (for scripted use)")
    parser.add_argument("--create-task", action="store_true",
                        help="Create a new task in a project (use with --project, --task-name)")
    parser.add_argument("--task-name", metavar="NAME",
                        help="Task name (required with --create-task)")
    parser.add_argument("--task-notes", metavar="NOTES", default="",
                        help="Task notes/description (optional with --create-task)")
    parser.add_argument("--task-assignee", metavar="GID", default="",
                        help="Assignee GID (optional; defaults to Mark's GID if not set)")
    parser.add_argument("--task-depends-on", metavar="GID", default="",
                        help="GID of the task this new task unblocks (optional)")
    args = parser.parse_args()

    if not ASANA_PAT:
        log.error("ERROR: ASANA_PAT not set. Add it to ~/dev/bain-studio/studio/.env")
        sys.exit(2)
    if not WORKSPACE_GID or not BAINBOT_GID:
        log.error("ERROR: ASANA_WORKSPACE_GID and ASANA_BAINBOT_GID must be set in .env")
        sys.exit(2)

    if args.create:
        missing = [f for f, v in [("--name", args.name), ("--prefix", args.prefix), ("--path", args.path)] if not v]
        if missing:
            parser.error(f"--create requires: {', '.join(missing)}")
        extra = [m.strip() for m in args.members.split(",")] if args.members else []
        scaffold_project(
            name=args.name,
            prefix=args.prefix.upper(),
            path=args.path,
            template_gid=args.template or TEMPLATE_PROJECT_GID,
            extra_members=extra,
            dry_run=args.dry_run,
            yes=args.yes,
        )
        sys.exit(0)

    if args.create_task:
        if not args.task_name:
            parser.error("--create-task requires --task-name")
        if not args.project:
            parser.error("--create-task requires --project (the task prefix, e.g. BD)")
        projects = discover_projects(filter_prefix=args.project)
        if not projects:
            log.error(f"No project found with prefix '{args.project}'.")
            sys.exit(1)
        proj = projects[0]
        assignee = args.task_assignee or USER_GID
        gid = create_task(
            project_gid=proj.gid,
            name=args.task_name,
            notes=args.task_notes,
            assignee_gid=assignee,
            depends_on_gid=args.task_depends_on or None,
            dry_run=args.dry_run,
        )
        print(gid)
        sys.exit(0)

    if args.setup:
        suffix = " [DRY-RUN]" if args.dry_run else ""
        log.info(f"=== Field setup{suffix} ===")
        projects = discover_projects(filter_prefix=args.project)
        if not projects:
            label = f"prefix '{args.project}'" if args.project else "any project"
            log.error(f"No projects discovered matching {label}.")
            sys.exit(1)
        for proj in projects:
            setup_project_fields(proj, dry_run=args.dry_run)
        log.info("\n=== Setup done ===")
        sys.exit(0)

    suffix = " [DRY-RUN]" if args.dry_run else ""
    log.info(f"=== Studio sync started{suffix} ===")

    projects = discover_projects(filter_prefix=args.project)
    if not projects:
        label = f"prefix '{args.project}'" if args.project else "any project"
        log.error(f"No projects discovered matching {label}.")
        log.info("Add ASANA_PROJECT_GID and ASANA_TASK_PREFIX to a project's CLAUDE.md.")
        sys.exit(1)

    log.info(f"{len(projects)} project(s) found:")
    for p in projects:
        log.info(f"  {p.prefix}: {p.name}")

    results = {}
    for proj in projects:
        results[proj.prefix] = sync_project(proj, dry_run=args.dry_run)

    if not args.dry_run and not args.project:
        write_registry(projects, results)
        log.info(f"\nRegistry written → {STUDIO_DIR / 'projects.md'}")

    failed = [k for k, ok in results.items() if not ok]
    if failed:
        log.error(f"\nFailed: {', '.join(failed)}")
        sys.exit(1)
    log.info(f"\n=== Done ===")


if __name__ == "__main__":
    main()

"""
Studio Asana sync — syncs assignee tasks across all active studio projects.

Scans STUDIO_SCAN_ROOTS for CLAUDE.md files containing ASANA_PROJECT_GID, then
syncs each project's Asana tasks to <project>/.claude/asana-mirror.md.

Required env vars (set in studio/.env):
    ASANA_PAT               Personal access token
    ASANA_WORKSPACE_GID     Workspace GID
    ASANA_BAINBOT_GID       GID of the Asana user tasks are assigned to
    ASANA_LOCAL_ID_FIELD_GID  GID of the custom text field used for local IDs

Projects registry: studio/projects.json (gitignored — copy from projects.example.json)

Usage:
    python sync.py                    # sync all discovered projects
    python sync.py --project MCF      # sync one project by prefix
    python sync.py --dry-run          # preview only, no writes or Asana mutations

Log: studio/sync.log (rotating, 5 MB × 3)
"""

import argparse
import logging
import os
import re
import sys
import json
import requests
from dataclasses import dataclass
from datetime import date, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

STUDIO_DIR = Path(__file__).parent
load_dotenv(STUDIO_DIR / ".env")

ASANA_PAT      = os.getenv("ASANA_PAT") or os.getenv("ASANA_TOKEN")
WORKSPACE_GID  = os.getenv("ASANA_WORKSPACE_GID")
BAINBOT_GID    = os.getenv("ASANA_BAINBOT_GID")
ASSIGNEE_NAME  = os.getenv("STUDIO_ASSIGNEE_NAME", "Bot")
TODAY         = date.today().isoformat()
BASE_URL      = "https://app.asana.com/api/1.0"

SKIP_PREFIXES = {"PIPE"}  # projects with their own sync scripts

JUNK_PATTERNS = re.compile(r"^- |😍|📰|\[Product Update\]", re.IGNORECASE)
PLAIN_CHECK   = re.compile(r"^Checked \d{4}-\d{2}-\d{2}\.$")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("sync")
    logger.setLevel(logging.DEBUG)

    # Console: plain message, same feel as print()
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    # File: timestamped, rotating so it never grows unbounded
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


def discover_projects(filter_prefix=None) -> list:
    """Read project roots from projects.json and load config from each CLAUDE.md."""
    if not PROJECTS_FILE.exists():
        log.error(f"No projects.json found at {PROJECTS_FILE}. Copy projects.example.json to get started.")
        return []

    try:
        roots = json.loads(PROJECTS_FILE.read_text())
    except Exception as e:
        log.error(f"Could not parse {PROJECTS_FILE}: {e}")
        return []

    projects = []
    seen_gids = set()

    for raw in roots:
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


# ---------------------------------------------------------------------------
# Local ID state
# ---------------------------------------------------------------------------

def load_ids(proj: ProjectConfig) -> dict:
    if proj.ids_file.exists():
        return json.loads(proj.ids_file.read_text())
    return {"custom_field_gid": None, "tasks": {}, "next_seq": 1, "posted_progress": {}}


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

SHARED_FIELD_GID = os.getenv("ASANA_LOCAL_ID_FIELD_GID", "")


def ensure_custom_field(proj: ProjectConfig, state: dict, dry_run=False) -> str:
    if state.get("custom_field_gid"):
        return state["custom_field_gid"]
    if dry_run:
        state["custom_field_gid"] = SHARED_FIELD_GID
        return SHARED_FIELD_GID
    log.info(f"  [{proj.prefix}] Attaching 'Local ID' field to project...")
    try:
        _post(f"/projects/{proj.gid}/addCustomFieldSetting", {"data": {
            "custom_field": SHARED_FIELD_GID, "is_important": True,
        }})
    except Exception as e:
        # Field may already be attached — that's fine
        if "already" not in str(e).lower():
            log.warning(f"  [{proj.prefix}] Note: could not attach field: {e}")
    state["custom_field_gid"] = SHARED_FIELD_GID
    save_ids(proj, state)
    return SHARED_FIELD_GID


# ---------------------------------------------------------------------------
# Task fetching
# ---------------------------------------------------------------------------

def fetch_tasks(proj: ProjectConfig, field_gid: str) -> list:
    log.info(f"  [{proj.prefix}] Fetching tasks from Asana...")
    params = {
        "completed_since": "now",
        "opt_fields": (
            "gid,name,notes,due_on,assignee.gid,projects.name,"
            "modified_at,permalink_url,custom_fields.gid,custom_fields.text_value"
        ),
        "limit": 100,
    }
    data = _get(f"/projects/{proj.gid}/tasks", params)["data"]
    tasks = [t for t in data
             if (t.get("assignee") or {}).get("gid") == BAINBOT_GID
             and not _is_junk(t)]
    for t in tasks:
        t["_local_id"] = None
        for cf in t.get("custom_fields", []):
            if cf.get("gid") == field_gid:
                t["_local_id"] = cf.get("text_value") or None
                break
    return tasks


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
        t["_local_id"] = lid  # set locally regardless of Asana write
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
# Mirror parsing
# ---------------------------------------------------------------------------

def parse_existing_mirror(proj: ProjectConfig) -> dict:
    if not proj.mirror_file.exists():
        return {}
    carried = {}
    pattern = re.compile(
        r"- \*\*Local ID:\*\* (.+?)\n"
        r"- \*\*Asana ID:\*\* (\d+)\n"
        r"- \*\*Due:\*\* (.+?)\n"
        r"- \*\*Notes:\*\* (.+?)\n"
        r"- \*\*Blockers:\*\* (.+?)\n"
        r"- \*\*Progress:\*\* (.+?)\n"
        r"- \*\*Modified:\*\* (.+?)\n",
    )
    for m in pattern.finditer(proj.mirror_file.read_text()):
        gid = m.group(2)
        carried[gid] = {
            "local_id": m.group(1).strip(),
            "due":      m.group(3).replace(" **(OVERDUE)**", "").strip(),
            "notes":    m.group(4).strip(),
            "blockers": m.group(5).strip(),
            "progress": m.group(6).strip(),
            "modified": m.group(7).strip(),
        }
    return carried


def parse_existing_task_gids(proj: ProjectConfig) -> set:
    if not proj.mirror_file.exists():
        return set()
    return set(re.findall(r"- \*\*Asana ID:\*\* (\d+)", proj.mirror_file.read_text()))


# ---------------------------------------------------------------------------
# Mirror building
# ---------------------------------------------------------------------------

def _trunc(text, n=300) -> str:
    text = text.strip().replace("\n", " ")
    return text[:n] + "..." if len(text) > n else text


def build_mirror(proj: ProjectConfig, tasks: list, carried: dict) -> str:
    lines = [
        f"# {ASSIGNEE_NAME} Asana Task Mirror",
        f"Last synced: {TODAY}",
        f"Workspace GID: {WORKSPACE_GID}",
        f"Assignee GID: {BAINBOT_GID}",
        "",
        f"## {proj.name}",
        "",
    ]
    for t in tasks:
        gid      = t["gid"]
        prev     = carried.get(gid, {})
        local_id = t.get("_local_id") or prev.get("local_id") or "—"
        blockers = prev.get("blockers") or "None identified."
        prev_p   = prev.get("progress", "")
        progress = f"Checked {TODAY}." if (not prev_p or PLAIN_CHECK.match(prev_p)) else prev_p
        notes    = _trunc(t.get("notes") or "") or "No notes."
        due      = t.get("due_on") or "none"
        overdue  = " **(OVERDUE)**" if due != "none" and due < TODAY else ""
        modified = (t.get("modified_at") or "")[:19]

        lines += [
            f"### {local_id} — {t['name']}",
            f"- **Local ID:** {local_id}",
            f"- **Asana ID:** {gid}",
            f"- **Due:** {due}{overdue}",
            f"- **Notes:** {notes}",
            f"- **Blockers:** {blockers}",
            f"- **Progress:** {progress}",
            f"- **Modified:** {modified}",
            f"- **URL:** {t.get('permalink_url', '')}",
            "",
        ]
    return "\n".join(lines)


def priorities_table(tasks: list) -> str:
    week_out = (date.today() + timedelta(days=7)).isoformat()
    overdue  = [t for t in tasks if t.get("due_on") and t["due_on"] < TODAY]
    due_soon = [t for t in tasks if t.get("due_on") and TODAY <= t["due_on"] <= week_out]
    no_due   = [t for t in tasks if not t.get("due_on")]

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
# Per-project sync
# ---------------------------------------------------------------------------

def sync_project(proj: ProjectConfig, dry_run=False) -> bool:
    log.info(f"\n[{proj.prefix}] {proj.name}")
    log.info(f"  Path: {proj.root}")
    log.info(f"  GID:  {proj.gid}")
    try:
        proj.claude_dir.mkdir(exist_ok=True)
        state     = load_ids(proj)
        field_gid = ensure_custom_field(proj, state, dry_run)

        tasks = fetch_tasks(proj, field_gid)
        log.info(f"  {len(tasks)} task(s) assigned to {ASSIGNEE_NAME}.")

        prev_gids    = parse_existing_task_gids(proj)
        curr_gids    = {t["gid"] for t in tasks}
        new_gids     = curr_gids - prev_gids
        removed_gids = prev_gids - curr_gids

        carried = parse_existing_mirror(proj)
        state   = assign_ids(proj, tasks, state, field_gid, dry_run)

        posted_progress = state.get("posted_progress", {})
        commented = 0
        for t in tasks:
            gid      = t["gid"]
            prev     = carried.get(gid)
            curr_p   = (prev or {}).get("progress", "")
            local_id = t.get("_local_id", "?")

            if (curr_p
                    and not PLAIN_CHECK.match(curr_p)
                    and curr_p != posted_progress.get(gid)):
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

        mirror = build_mirror(proj, tasks, carried)

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

        log.info(f"  {len(new_gids)} new | {len(removed_gids)} removed | {commented} comment(s) posted")
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
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Studio Asana sync")
    parser.add_argument("--project", metavar="PREFIX",
                        help="Sync a single project by its ASANA_TASK_PREFIX (e.g. MCF)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discover and preview — no writes to mirrors or Asana")
    args = parser.parse_args()

    if not ASANA_PAT:
        log.error("ERROR: ASANA_PAT not set. Add it to ~/dev/bain-studio/studio/.env")
        sys.exit(2)
    if not WORKSPACE_GID or not BAINBOT_GID:
        log.error("ERROR: ASANA_WORKSPACE_GID and ASANA_BAINBOT_GID must be set in .env")
        sys.exit(2)

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

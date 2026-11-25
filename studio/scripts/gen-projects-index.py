#!/usr/bin/env python3
"""Generate PmBot's projects index from the registry.

The index (`$STUDIO_CONTENT_DIR/projects-index.md`) is what PmBot reads at the
start of every session. It used to be written by hand, which makes it a fifth
copy of project identity, the drift ADR 021 exists to end. This regenerates its
table from `registry.json` instead.

Only the table is generated. Everything else in the file (the intro line,
"Shared locations", "Adding a project") is prose a human owns, so it is carried
over from the existing file unchanged. With no existing file, a default is used.

Columns, and where each comes from:

    Prefix           registry `prefix`
    Project          registry `name`
    Asana project    Asana project name, fetched read-only with the bainbot PAT
    Asana GID        registry `gid`
    Dropbox folder   registry `dropbox`, else `client_docs`, else "none"
    Missions folder  `missions/` when that folder exists in the Dropbox folder
    Agent            registry `agent`, else "DevBot"

Only `status: active` is listed: paused, inactive and archived are left out.

Usage:
    python3 studio/scripts/gen-projects-index.py               # print to stdout
    python3 studio/scripts/gen-projects-index.py --write       # rewrite the index
    python3 studio/scripts/gen-projects-index.py --no-asana    # skip the API call

Overrides: BAIN_REGISTRY (see registry.py), BAIN_PROJECTS_INDEX (the index
file), BAIN_STUDIO_ENV (the .env holding ASANA_PAT and STUDIO_CONTENT_DIR).
"""

import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
sys.path.insert(0, str(STUDIO))

import registry  # noqa: E402

DROPBOX_ROOT = Path("/media/data/Dropbox")
DEFAULT_AGENT = "DevBot"
NONE = "none"

HEADER = "| Prefix | Project | Asana project | Asana GID | Dropbox folder | Missions folder | Agent |"
RULE = "|---|---|---|---|---|---|---|"

DEFAULT_INTRO = (
    "# Studio Projects Index\n\n"
    "Master list of active Bain Design projects. PmBot reads this at the start of every session. "
    "Add a row whenever a new project starts.\n"
)
DEFAULT_TAIL = (
    "## Adding a project\n\n"
    "1. Create the Asana project with a prefix, e.g. `[ABC] project-name`, and add PmBot and DevBot.\n"
    "2. Create the Dropbox project folder with a `missions/` subfolder.\n"
    "3. Add a row to the table above.\n"
)
GENERATED_NOTE = (
    "<!-- The table below is generated from the studio registry by "
    "studio/scripts/gen-projects-index.py. Edit the registry, then regenerate. -->"
)


def _load_env():
    """Read ASANA_PAT and STUDIO_CONTENT_DIR without importing sync.py, which
    sets up logging and a great deal else on import."""
    candidates = []
    if os.environ.get("BAIN_STUDIO_ENV"):
        candidates.append(Path(os.environ["BAIN_STUDIO_ENV"]).expanduser())
    candidates.append(STUDIO / ".env")
    config_home = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    candidates.append(Path(config_home) / "bain-studio" / ".env")
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for c in candidates:
        if c.is_file():
            load_dotenv(c)
            return


def index_path() -> Path:
    if os.environ.get("BAIN_PROJECTS_INDEX"):
        return Path(os.environ["BAIN_PROJECTS_INDEX"]).expanduser()
    content = os.environ.get("STUDIO_CONTENT_DIR") or "/media/data/Dropbox/Work/Studio/context"
    return Path(content).expanduser() / "projects-index.md"


def asana_project_names(gids, enabled=True) -> dict:
    """GID -> Asana project name. Read-only GETs. Empty on any failure: a
    missing name is reported as such, never invented."""
    pat = os.environ.get("ASANA_PAT") or os.environ.get("ASANA_TOKEN")
    if not enabled or not pat:
        return {}
    try:
        import requests
    except ImportError:
        return {}
    out = {}
    for gid in gids:
        try:
            r = requests.get(
                f"https://app.asana.com/api/1.0/projects/{gid}",
                headers={"Authorization": f"Bearer {pat}", "Accept": "application/json"},
                params={"opt_fields": "name,archived"},
                timeout=15,
            )
            if r.ok:
                out[gid] = r.json().get("data", {}).get("name", "")
        except requests.RequestException:
            continue
    return out


def short_dropbox(path: str) -> str:
    """/media/data/Dropbox/Work/x -> /Work/x/, the form the index uses."""
    p = Path(path)
    try:
        rel = p.relative_to(DROPBOX_ROOT)
    except ValueError:
        return str(p)
    return "/" + str(rel).rstrip("/") + "/"


def row(entry: dict, names: dict, asana_fetched: bool) -> str:
    gid = (entry.get("gid") or "").strip()
    if not gid:
        asana_name = NONE
    elif gid in names:
        asana_name = names[gid] or NONE
    else:
        asana_name = "(not fetched)" if not asana_fetched else "(not found)"

    dropbox = entry.get("dropbox") or entry.get("client_docs") or ""
    if dropbox and Path(dropbox).is_dir():
        dropbox_cell = f"`{short_dropbox(dropbox)}`"
        missions_cell = "`missions/`" if (Path(dropbox) / "missions").is_dir() else NONE
    elif dropbox:
        dropbox_cell = f"`{short_dropbox(dropbox)}` (missing)"
        missions_cell = NONE
    else:
        dropbox_cell = NONE
        missions_cell = NONE

    cells = [
        entry.get("prefix", ""),
        entry.get("name", "") or NONE,
        asana_name,
        gid or NONE,
        dropbox_cell,
        missions_cell,
        entry.get("agent") or DEFAULT_AGENT,
    ]
    return "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |"


def split_existing(text: str):
    """(intro, tail) around the table. The table is the first block of lines
    starting with '|'; anything else is human prose and is kept."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("| Prefix")), None)
    if start is None:
        return None
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    intro = [l for l in lines[:start] if l.strip() != GENERATED_NOTE]
    return "\n".join(intro).rstrip() + "\n", "\n".join(lines[end:]).strip() + "\n"


def build(existing: str, entries: dict, names: dict, asana_fetched: bool) -> str:
    parts = split_existing(existing) if existing else None
    intro, tail = parts if parts else (DEFAULT_INTRO, DEFAULT_TAIL)
    active = sorted(
        (e for e in entries.values() if (e.get("status") or "").lower() == "active"),
        key=lambda e: (e.get("prefix") or "").upper(),
    )
    table = [HEADER, RULE] + [row(e, names, asana_fetched) for e in active]
    return f"{intro}\n{GENERATED_NOTE}\n\n" + "\n".join(table) + f"\n\n{tail}"


def main():
    ap = argparse.ArgumentParser(description="Generate the projects index from the registry.")
    ap.add_argument("--write", action="store_true", help="rewrite the index file in place")
    ap.add_argument("--no-asana", action="store_true", help="do not fetch Asana project names")
    args = ap.parse_args()

    _load_env()
    entries, source = registry.load()
    if source != registry.SOURCE_REGISTRY or not entries:
        print(f"gen-projects-index: no registry at {registry.registry_path()}; refusing "
              "to build the index from the fallback", file=sys.stderr)
        return 2

    gids = sorted({(e.get("gid") or "").strip() for e in entries.values()
                   if (e.get("status") or "").lower() == "active" and e.get("gid")})
    names = asana_project_names(gids, enabled=not args.no_asana)
    asana_fetched = bool(names)

    target = index_path()
    existing = target.read_text() if target.is_file() else ""
    out = build(existing, entries, names, asana_fetched)

    if args.write:
        target.write_text(out)
        print(f"gen-projects-index: wrote {target}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

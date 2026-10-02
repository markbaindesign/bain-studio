#!/usr/bin/env python3
"""
Daily Brief — the studio's chief of staff.

Sweeps the studio every morning for things that are slipping, ranks them, writes a
dated note into the Obsidian vault, and pings Slack with the top items and a link to
the note. Deterministic: no Claude call, no API cost.

Areas:
  Finance     books not updated, account shortfalls, tax filing deadlines,
              month-on-month losses, open money tasks (invoices, budgets, renewals)
  Operations  scheduled jobs that are erroring or have gone quiet, stale finance
              snapshot, uncommitted work, unmerged feature branches
  Projects    overdue tasks assigned to Mark, looper tasks blocked on Mark, work waiting in Review,
              projects with no activity
  Clients     tasks waiting on a client (chase, sign-off, client action) gone quiet
  Voice notes transcripts from audio_notes.py not yet marked reviewed; silent recordings

Escalation: every finding has a stable key. studio/collectors/daily_brief_state.json
records when each was first raised; a finding still open after 7 days goes up one
severity level, and the note says how long it has been ignored. Resolved findings
drop out of the state file.

Note:   $OBSIDIAN_VAULT/Daily Brief/YYYY-MM-DD-daily-brief.md  (reruns overwrite)
        Override the folder with DAILY_BRIEF_DIR.

Usage:
  python3 studio/collectors/daily_brief.py              # write note, update state, notify
  python3 studio/collectors/daily_brief.py --dry-run    # print the note; no writes, no Slack
  python3 studio/collectors/daily_brief.py --no-notify  # write the note, skip Slack

Cron (runs from the ops worktree, after sync, Hermes and the GnuCash collector):
  40 8 * * * cd /home/bain/ops/bain-studio && python3 studio/collectors/daily_brief.py >> studio/collectors/daily_brief.log 2>&1
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv

COLLECTORS_DIR = Path(__file__).resolve().parent
STUDIO_DIR = COLLECTORS_DIR.parent
load_dotenv(STUDIO_DIR / ".env")
sys.path.insert(0, str(STUDIO_DIR))
sys.path.insert(0, str(STUDIO_DIR / "dashboard"))

STATE_FILE = COLLECTORS_DIR / "daily_brief_state.json"
PROJECTS_FILE = STUDIO_DIR / "projects.json"
LOG_PREFIX = "[daily_brief]"

SEVERITIES = ["normal", "high", "critical"]
BOOKS_STALE_DAYS = 14
BUSY_ACCOUNT_ENTRIES = 10
DORMANT_AFTER_DAYS = 180  # untouched this long: a dormant account, not a books backlog
OVERDUE_ROLLUP = 5  # more overdue tasks than this in one project: one summary finding instead
UNTOUCHED_AFTER_DAYS = 60  # an open task nobody has touched this long has been dropped
UNTOUCHED_HIGH_DAYS = 180  # ...and this long means it is not coming back on its own
PROJECT_STALE_HIGH_DAYS = 90  # a registered active project silent this long
QUIET_CYCLES_HIGH = 3  # a job silent for this many of its own cycles is dead, not late
UNTOUCHED_ROLLUP = 5  # as OVERDUE_ROLLUP, for untouched tasks
VOICE_NOTE_STALE_DAYS = 7  # an untriaged voice note is not urgent before this

# Jobs whose cron log is not where they report: check this file's freshness instead.
QUIET_JOB_LOGS = {
    "looper_runner.py": Path.home() / "logs" / "studio-looper.log",
}

FINANCE_RE = re.compile(r"\b(invoice|budget|books|bookkeep|tax|iva|irpf|mod\.? ?\d{3}|gestor|"
                        r"payment|renew|licen[cs]e|subscription|harvest)\b", re.I)
CLIENT_RE = re.compile(r"(\bchase\b|sign.?off|client action|confirm with client|waiting on|"
                       r"awaiting|follow.?up|^OQ\d+)", re.I)
MIRROR_FIELD_RE = re.compile(r"^- \*\*([^:]+):\*\* ?(.*)$")
ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

def finding(key, area, severity, title, detail="", url="", age_days=None, group="", acute=False):
    """acute: something is erroring right now, as opposed to rotting slowly.

    Ranking by age alone cannot express this. A job that failed on its last run has an age of
    zero and would sort below a task 476 days overdue, though only one of them is actually
    broken. Acute findings sort above chronic ones of the same severity.
    """
    return {"key": key, "area": area, "severity": severity, "title": title, "detail": detail,
            "url": url, "age_days": age_days, "group": group, "acute": acute}


def _days_since(iso, today):
    try:
        return (today - dt.date.fromisoformat(iso[:10])).days
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Mirrors
# ---------------------------------------------------------------------------

def load_registry():
    try:
        return json.loads(PROJECTS_FILE.read_text())
    except (OSError, ValueError):
        return []


def parse_mirror(text):
    """Open tasks from an asana-mirror.md: sections DONE and the priorities table are skipped."""
    tasks = []
    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        heading = part.split("\n", 1)[0].strip().upper()
        if heading in ("DONE", "IMMEDIATE PRIORITIES"):
            continue
        for block in re.split(r"\n(?=### )", part)[1:]:
            head = block.split("\n", 1)[0][4:]
            lid, _, name = head.partition(" — ")
            fields, key = {}, None
            for line in block.split("\n")[1:]:
                m = MIRROR_FIELD_RE.match(line)
                if m:
                    key = m.group(1).lower()
                    fields[key] = m.group(2).strip()
                elif key == "notes" and line.strip():
                    fields["notes"] += " " + line.strip()
            section = fields.get("section", "")
            looper = fields.get("looper status", "")
            if section.upper() == "DONE" or looper.lower() == "done":
                continue
            due = fields.get("due", "none").replace("**(OVERDUE)**", "").strip()
            tasks.append({
                "lid": lid.strip(), "name": name.strip() or "(untitled)",
                "section": section, "looper": looper, "due": due,
                "notes": fields.get("notes", ""), "blockers": fields.get("blockers", ""),
                "progress": fields.get("progress", ""), "modified": fields.get("modified", ""),
                "url": fields.get("url", ""), "assignee": fields.get("assignee", ""),
            })
    return tasks


def assigned_to_me(task, user_gid):
    """The brief is Mark's safety net: tasks assigned to anyone else (or nobody) are not his to chase."""
    return bool(user_gid) and f"({user_gid})" in task["assignee"]


def load_project_tasks():
    """{prefix: {"status", "tasks"}} for every registered project with a mirror, SL/SLT excluded
    (their tasks are multi-homed and already appear in their home mirrors). Only tasks
    assigned to ASANA_USER_GID are kept."""
    user_gid = os.getenv("ASANA_USER_GID", "")
    projects = {}
    for entry in load_registry():
        root = Path(entry["path"]).expanduser()
        mirror, claude_md = root / "asana-mirror.md", root / "CLAUDE.md"
        if not mirror.exists() or "looper" in root.parts[-1]:
            continue
        try:
            m = re.search(r"ASANA_TASK_PREFIX:\s*(\S+)", claude_md.read_text(errors="replace"))
        except OSError:
            continue
        if not m or m.group(1) in ("SL", "SLT"):
            continue
        projects[m.group(1)] = {"status": entry.get("status", "active"), "root": root,
                                "tasks": [t for t in parse_mirror(mirror.read_text(errors="replace"))
                                          if assigned_to_me(t, user_gid)]}
    return projects


# ---------------------------------------------------------------------------
# Task checks (Projects, Clients, Finance tasks)
# ---------------------------------------------------------------------------

def task_area(task):
    text = f"{task['name']} {task['notes'][:300]}"
    if FINANCE_RE.search(task["name"]):
        return "Finance"
    if CLIENT_RE.search(text):
        return "Clients"
    return "Projects"


def check_tasks(projects, today):
    out = []
    for prefix, proj in projects.items():
        if proj["status"] in ("paused", "archived"):
            continue
        last_activity = None
        for t in proj["tasks"]:
            mod_age = _days_since(t["modified"], today)
            if mod_age is not None:
                last_activity = mod_age if last_activity is None else min(last_activity, mod_age)
            area = task_area(t)
            label = f"{t['lid']} — {t['name']}"
            base = {"url": t["url"], "group": prefix}

            if t["looper"].lower() == "blocked":
                m = ISO_DATE_RE.search(t["blockers"])
                age = _days_since(m.group(1), today) if m else mod_age
                reason = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[—-]\s*", "", t["blockers"])[:160]
                out.append(finding(f"task:{t['lid']}:blocked", "Projects",
                                   "high" if (age or 0) > 14 else "normal",
                                   label, f"blocked, waiting on you: {reason}",
                                   age_days=age, **base))
                continue

            overdue = _days_since(t["due"], today) if t["due"] != "none" else None
            if overdue is not None and overdue > 0:
                sev = "high" if overdue > 14 or area == "Finance" else "normal"
                out.append(finding(f"task:{t['lid']}:overdue", area, sev, label,
                                   f"{overdue} day(s) overdue (due {t['due']})",
                                   age_days=overdue, **base))
                continue

            if t["looper"].lower() == "review":
                m = re.search(r"(?:Ready for review|review)\D{0,3}(\d{4}-\d{2}-\d{2})", t["progress"], re.I)
                age = _days_since(m.group(1), today) if m else mod_age
                if age is not None and age > 7:
                    out.append(finding(f"task:{t['lid']}:review", "Projects",
                                       "high" if age > 21 else "normal", label,
                                       f"done, waiting for your review for {age} days",
                                       age_days=age, **base))
                continue

            if area == "Clients" and mod_age is not None and mod_age > 14:
                out.append(finding(f"task:{t['lid']}:client", "Clients",
                                   "high" if mod_age > 30 else "normal", label,
                                   f"waiting on the client, no movement for {mod_age} days",
                                   age_days=mod_age, **base))
            elif mod_age is not None and mod_age > UNTOUCHED_AFTER_DAYS:
                # No due date, not blocked, not in review: nothing else would ever surface it.
                out.append(finding(f"task:{t['lid']}:untouched", area,
                                   "high" if mod_age > UNTOUCHED_HIGH_DAYS else "normal", label,
                                   f"open and untouched for {mod_age} days",
                                   age_days=mod_age, **base))

        overdue_here = [f for f in out if f["group"] == prefix and f["key"].endswith(":overdue")]
        if len(overdue_here) > OVERDUE_ROLLUP:
            oldest = max(f["age_days"] for f in overdue_here)
            for f in overdue_here:
                f["severity"], f["today"] = "normal", False
            out.append(finding(f"project:{prefix}:overdue-pile", "Projects", "high",
                               f"{prefix}: {len(overdue_here)} overdue tasks, oldest {oldest} days",
                               "the plan no longer matches reality. Reschedule, pause the project, "
                               "or close what's dead. Tasks listed below.",
                               age_days=oldest, group=prefix))

        untouched_here = [f for f in out if f["group"] == prefix and f["key"].endswith(":untouched")]
        if len(untouched_here) > UNTOUCHED_ROLLUP:
            oldest = max(f["age_days"] for f in untouched_here)
            for f in untouched_here:
                f["today"] = False
            out.append(finding(f"project:{prefix}:untouched-pile", "Projects",
                               "high" if oldest > UNTOUCHED_HIGH_DAYS else "normal",
                               f"{prefix}: {len(untouched_here)} tasks untouched for over "
                               f"{UNTOUCHED_AFTER_DAYS} days, oldest {oldest}",
                               "nothing else surfaces these. Close what's dead or pick one up. "
                               "Tasks listed below.",
                               age_days=oldest, group=prefix))

        if proj["status"] == "active" and proj["tasks"] and last_activity is not None and last_activity > 30:
            out.append(finding(f"project:{prefix}:stale", "Projects",
                               "high" if last_activity > PROJECT_STALE_HIGH_DAYS else "normal",
                               f"{prefix} has had no task activity for {last_activity} days",
                               f"{len(proj['tasks'])} open task(s); close, pause or pick it up",
                               age_days=last_activity, group="Stale projects"))
    return out


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------

def _finance_dir():
    return Path(os.getenv("FINANCE_DATA_DIR", ""))


def check_books(today):
    """Latest transaction date per current-assets account in the GnuCash book."""
    path = os.getenv("GNUCASH_FILE")
    if not path or not Path(path).exists():
        return [finding("finance:gnucash-missing", "Finance", "high",
                        "GnuCash book not found", "GNUCASH_FILE is unset or points nowhere",
                        acute=True)]
    try:
        import gzip
        import xml.etree.ElementTree as ET
        import gnucash_parser
        opener = gzip.open if gnucash_parser._is_gzip(path) else open
        with opener(path, "rb") as f:
            book = ET.fromstring(f.read()).find("gnc:book", gnucash_parser.NS)
        ns = gnucash_parser.NS
        accounts = {}
        for acc in book.findall("gnc:account", ns):
            aid = acc.find("act:id", ns)
            if aid is not None:
                accounts[aid.text] = {
                    "name": (acc.find("act:name", ns).text if acc.find("act:name", ns) is not None else "?"),
                    "parent": (acc.find("act:parent", ns).text if acc.find("act:parent", ns) is not None else None),
                }
        for aid in accounts:
            accounts[aid]["path"] = gnucash_parser._get_path(aid, {k: {**v, "path": ""} for k, v in accounts.items()})
        from fractions import Fraction
        dates, balance = {}, {}
        for trn in book.findall("gnc:transaction", ns):
            d = trn.find("trn:date-posted/ts:date", ns)
            if d is None:
                continue
            day = d.text[:10]
            for sp in trn.findall("trn:splits/trn:split", ns):
                a, q = sp.find("split:account", ns), sp.find("split:quantity", ns)
                if a is not None and a.text in accounts and re.search(r"(^|:)Current Assets:", accounts[a.text]["path"]):
                    dates.setdefault(a.text, []).append(day)
                    balance[a.text] = balance.get(a.text, 0.0) + (float(Fraction(q.text)) if q is not None else 0.0)
    except Exception as e:
        return [finding("finance:gnucash-unreadable", "Finance", "high",
                        "Could not read the GnuCash book", str(e)[:200], acute=True)]

    # Only accounts in real use: holding money, or busy in the 90 days before their last entry.
    # Closed or dormant accounts (zero balance, a handful of entries) would otherwise read as stale.
    stale = []
    for aid, days in dates.items():
        last = max(days)
        window_start = (dt.date.fromisoformat(last) - dt.timedelta(days=90)).isoformat()
        busy = sum(1 for d in days if d > window_start) >= BUSY_ACCOUNT_ENTRIES
        if abs(balance.get(aid, 0.0)) < 0.005 and not busy:
            continue
        age = _days_since(last, today)
        if age is not None and BOOKS_STALE_DAYS < age < DORMANT_AFTER_DAYS:
            stale.append((age, accounts[aid]["path"].split("Current Assets:", 1)[-1], last))
    if not stale:
        return []
    stale.sort(reverse=True)
    worst = stale[0][0]
    detail = "; ".join(f"{name} last entry {day}" for _, name, day in stale)
    return [finding("finance:books-stale", "Finance", "critical" if worst > 30 else "high",
                    f"Books are {worst} days behind", detail + ". Run /bookkeeper.", age_days=worst)]


def check_snapshot(today):
    """accounts.json from the GnuCash collector: shortfalls, losses, staleness."""
    path = _finance_dir() / "accounts.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        return [finding("ops:snapshot-missing", "Operations", "high",
                        "Finance snapshot (accounts.json) unreadable", str(e)[:200], acute=True)]
    out = []
    age = _days_since(data.get("generated_at", ""), today)
    if age is None or age > 2:
        out.append(finding("ops:snapshot-stale", "Operations", "high",
                           "Finance snapshot is stale",
                           f"accounts.json generated {data.get('generated_at', 'never')}; "
                           f"gnucash_collector.py has not run successfully since", age_days=age))

    bbva = data.get("bbva_forecast") or {}
    if bbva.get("shortfall"):
        out.append(finding("finance:bbva-shortfall", "Finance", "critical",
                           "BBVA will go overdrawn within 30 days",
                           f"€{bbva.get('balance', 0):,.2f} now, €{bbva.get('due_30d', 0):,.2f} due, "
                           f"€{bbva.get('balance_after_30d', 0):,.2f} after 30 days. "
                           "Move money in or reschedule a payment. (Forecast is only as current as the books.)"))
    if data.get("balance_after_30d", 0) < 0:
        out.append(finding("finance:liquid-negative", "Finance", "critical",
                           "Liquid cash goes negative within 30 days",
                           f"€{data.get('balance_after_30d'):,.2f} after upcoming payments"))

    months = data.get("monthly_pl_recent") or []
    closed = [m for m in months if m.get("month") != today.strftime("%Y-%m")]
    losing = [m for m in closed if m.get("net", 0) < 0]
    if len(closed) >= 2 and len(losing) == len(closed):
        detail = ", ".join(f"{m['month']} €{m['net']:,.0f}" for m in closed)
        out.append(finding("finance:running-at-loss", "Finance", "high",
                           f"Below break-even for {len(closed)} months running",
                           f"Net after owner draw: {detail}. Break-even is "
                           f"€{data.get('breakeven_allin', 0):,.0f}/month."))
    return out


def check_tax(today):
    try:
        import gnucash_parser
        quarter_end, filing = gnucash_parser._next_mod130_filing(today)
        confirmed = {f["due_date"] for f in gnucash_parser._load_confirmed_tax_filings()}
    except Exception as e:
        return [finding("finance:tax-unknown", "Finance", "normal",
                        "Could not work out the next tax filing", str(e)[:200])]
    if not filing or filing in confirmed:
        return []
    days = (filing - today).days
    if days > 45:
        return []
    q = (quarter_end.month - 1) // 3 + 1
    sev = "critical" if days <= 10 else "high" if days <= 30 else "normal"
    return [finding(f"finance:tax-{quarter_end.year}-Q{q}", "Finance", sev,
                    f"Q{q} {quarter_end.year} quarterly returns due in {days} days ({filing})",
                    "Mod 303 / 130 / 111. Books must be current first; not yet logged as filed "
                    "in aletheia-codex.md.")]


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def _cron_max_age_hours(schedule):
    minute, hour, dom, month, dow = schedule
    if hour == "*":
        return 3
    if dom == "*" and dow == "*":
        return 30
    if dow != "*":
        days = [int(d) for d in re.split(r"[,-]", dow) if d.isdigit()]
        gap = 7 if len(days) <= 1 else max(((b - a) % 7 or 7) for a, b in zip(days, days[1:] + days[:1]))
        return gap * 24 + 6
    return 32 * 24


def _tail(path, lines=40):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 16000))
            return f.read().decode(errors="replace").splitlines()[-lines:]
    except OSError:
        return []


def check_cron(today, crontab_text=None, now=None):
    now = now or dt.datetime.now()
    if crontab_text is None:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        crontab_text = r.stdout
    out = []
    for line in crontab_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" in line.split()[0]:
            continue
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        schedule, command = parts[:5], parts[5]
        log_m = re.search(r">>\s*(\S+)", command)
        if not log_m:
            continue
        cd_m = re.search(r"cd\s+(\S+)", command)
        base = Path(os.path.expandvars(cd_m.group(1).replace("$HOME", str(Path.home())))) if cd_m else Path.home()
        log = Path(os.path.expandvars(log_m.group(1).replace("$HOME", str(Path.home()))))
        log = log if log.is_absolute() else base / log
        script_m = re.search(r"([\w./-]+\.py)", command)
        job = Path(script_m.group(1)).name if script_m else command.split(">>")[0].strip()[-40:]
        max_age = _cron_max_age_hours(schedule)
        key = f"ops:cron:{job}"

        watched = QUIET_JOB_LOGS.get(job, log)
        if not watched.exists():
            out.append(finding(key, "Operations", "normal", f"Scheduled job {job} has no log yet",
                               f"expected {watched}; it may not have run since it was added"))
            continue
        hours = (now - dt.datetime.fromtimestamp(watched.stat().st_mtime)).total_seconds() / 3600
        if hours > max_age:
            # Silent for several of its own cycles is a dead job, not a late one.
            out.append(finding(key, "Operations",
                               "high" if hours > max_age * QUIET_CYCLES_HIGH else "normal",
                               f"Scheduled job {job} has gone quiet",
                               f"{watched.name} last written {hours / 24:.0f} day(s) ago, expected every "
                               f"~{max_age}h. Either it isn't running or it logs nothing on success",
                               age_days=int(hours // 24)))
            continue
        if job in QUIET_JOB_LOGS:
            continue
        tail = [l for l in _tail(log) if l.strip()][-6:]
        err = next((l for l in tail if re.search(r"Traceback|^\w*Error\b|\bERROR\b|^Failed:", l)), None)
        if err:
            last = next((l for l in reversed(tail) if l.strip()), "")
            out.append(finding(key, "Operations", "high", f"Scheduled job {job} is failing",
                               f"latest run ends: {last.strip()[:180]}", acute=True))
    return out


def _git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
    return r.stdout if r.returncode == 0 else None


def check_repos(projects, today):
    out = []
    for prefix, proj in projects.items():
        root = proj["root"]
        if proj["status"] in ("paused", "archived") or not (root / ".git").exists():
            continue
        status = _git(root, "status", "--porcelain")
        if status:
            files = [l[3:].split(" -> ")[-1] for l in status.splitlines() if l[:2] != "??"]
            ages = []
            for f in files:
                p = root / f
                if p.exists():
                    ages.append((dt.date.today() - dt.date.fromtimestamp(p.stat().st_mtime)).days)
            oldest = max(ages) if ages else 0
            if files and oldest > 7:
                out.append(finding(f"ops:uncommitted:{prefix}", "Operations",
                                   "high" if oldest > 21 else "normal",
                                   f"{prefix}: {len(files)} uncommitted change(s), oldest {oldest} days",
                                   f"{root}. Commit, stash or discard.", age_days=oldest))
        if _git(root, "rev-parse", "--verify", "--quiet", "develop") is None:
            continue
        refs = _git(root, "for-each-ref", "refs/heads", "--no-merged", "develop",
                    "--format=%(refname:short) %(committerdate:short)") or ""
        stale = []
        for line in refs.splitlines():
            name, _, day = line.partition(" ")
            age = _days_since(day, today)
            if name.startswith(("feature/", "release/", "hotfix/")) and age is not None and age > 14:
                stale.append(f"{name} ({age}d)")
        if stale:
            out.append(finding(f"ops:branches:{prefix}", "Operations", "normal",
                               f"{prefix}: {len(stale)} unmerged branch(es) older than 2 weeks",
                               ", ".join(stale[:6])))
    return out


# ---------------------------------------------------------------------------
# Voice notes
# ---------------------------------------------------------------------------

def check_voice_notes(today):
    """Transcripts from audio_notes.py still marked reviewed: false, and recordings that came out silent."""
    vault = os.getenv("OBSIDIAN_VAULT")
    if not vault:
        return []
    out = []
    for note in sorted((Path(vault) / "Transcripts").glob("*.md")):
        try:
            head = note.read_text(errors="replace").split("\n---\n", 1)[0]
        except OSError:
            continue
        if not re.search(r"^reviewed:\s*false\s*$", head, re.M):
            continue
        rec = re.search(r"^recorded:\s*(\S+)", head, re.M)
        age = _days_since(rec.group(1), today) if rec else None
        tasks = re.search(r"^tasks:\s*\[(.*)\]", head, re.M)
        tasks = tasks.group(1).strip() if tasks else ""
        about = re.search(r"^\*\*About:\*\*\s*(.+)$", note.read_text(errors="replace"), re.M)
        detail = about.group(1)[:140] if about else (f"tasks: {tasks}" if tasks else "no task attached")
        out.append(finding(f"voice:{note.stem}", "Voice notes",
                           "high" if (age or 0) > VOICE_NOTE_STALE_DAYS else "normal",
                           note.stem, detail, url=obsidian_uri(note), age_days=age))
    try:
        state = json.loads((COLLECTORS_DIR / "audio_notes_state.json").read_text())
    except (OSError, ValueError):
        state = {}
    for path, entry in state.items():
        if entry.get("status") == "silent" and (_days_since(entry.get("checked", ""), today) or 0) <= 7:
            out.append(finding(f"voice:silent:{Path(path).name}", "Voice notes", "normal",
                               f"{Path(path).name} was silent",
                               f"mean volume {entry.get('mean_db')} dB, not transcribed. Check the mic input "
                               "(Scarlett gain, or Obsidian using the webcam mic)"))
        elif entry.get("status") == "failed" and entry.get("attempts", 0) >= 3:
            out.append(finding(f"voice:failed:{Path(path).name}", "Operations", "high",
                               f"Could not transcribe {Path(path).name}", entry.get("error", "")[:160],
                               acute=True))
    return out


# ---------------------------------------------------------------------------
# State, ranking, rendering
# ---------------------------------------------------------------------------

def stamp_first_seen(findings, state, today):
    """Record when each finding was first raised. Severity is not touched here.

    Severity belongs to the thing itself: how many days a task is overdue, how long a job has
    been silent, how far behind the books are. Every check derives it from that age already, so
    a second bump based on how long a finding had sat on the list counted age twice and, worse,
    ratcheted: on 2026-09-30 the brief carried 58 criticals, 57 of them promoted by the clock
    rather than by any check. first_seen now only feeds the "raised N days ago" line and breaks
    ties in ranking.
    """
    new_state = {}
    for f in findings:
        first = state.get(f["key"], today.isoformat())
        new_state[f["key"]] = first
        f["raised_days"] = _days_since(first, today) or 0
    return new_state


def rank(f):
    """Severity, then failing-now ahead of rotting, then the age of the problem, then how long
    we have been reporting it."""
    return (-SEVERITIES.index(f["severity"]), -int(f.get("acute", False)),
            -(f.get("age_days") or 0), -(f.get("raised_days") or 0))


def _line(f):
    title = f"[{f['title']}]({f['url']})" if f["url"] else f"**{f['title']}**"
    bits = [f"`{f['severity']}`", title]
    if f["detail"]:
        bits.append(f"- {f['detail']}")
    if f.get("raised_days"):
        bits.append(f"*(raised {f['raised_days']} day(s) ago)*")
    return "- " + " ".join(bits)


def render(findings, today):
    findings = sorted(findings, key=rank)
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
    lines = [
        "---", "tags: [daily-brief, studio]", f"date: {today}",
        f"critical: {counts['critical']}", f"high: {counts['high']}", f"normal: {counts['normal']}",
        "---", "", f"# Daily Brief - {today}", "",
        f"{counts['critical']} critical, {counts['high']} high, {counts['normal']} normal. "
        "Generated by `studio/collectors/daily_brief.py`.", "",
        "## Today", "",
    ]
    eligible = [f for f in findings if f.get("today", True)]
    top = [f for f in eligible if f["severity"] != "normal"][:8] or eligible[:5]
    lines += [_line(f) for f in top] or ["Nothing pressing."]

    for area in ("Voice notes", "Finance", "Operations", "Projects", "Clients"):
        items = [f for f in findings if f["area"] == area]
        lines += ["", f"## {area}", ""]
        if not items:
            lines.append("Nothing slipping.")
            continue
        groups = {}
        for f in items:
            groups.setdefault(f["group"], []).append(f)
        for group, fs in sorted(groups.items(), key=lambda kv: rank(kv[1][0])):
            if group:
                lines += ["", f"### {group}", ""]
            lines += [_line(f) for f in fs]
    return "\n".join(lines) + "\n", counts, top


def brief_dir():
    override = os.getenv("DAILY_BRIEF_DIR")
    if override:
        return Path(override)
    vault = os.getenv("OBSIDIAN_VAULT")
    return Path(vault) / "Daily Brief" if vault else COLLECTORS_DIR / "daily_brief_notes"


def obsidian_uri(path):
    vault = os.getenv("OBSIDIAN_VAULT")
    if not vault:
        return ""
    try:
        rel = path.relative_to(Path(vault)).with_suffix("")
    except ValueError:
        return ""
    return ("obsidian://open?vault=" + urllib.parse.quote(Path(vault).name)
            + "&file=" + urllib.parse.quote(str(rel)))


def collect(today):
    projects = load_project_tasks()
    findings = []
    for check in (lambda: check_books(today), lambda: check_snapshot(today), lambda: check_tax(today),
                  lambda: check_cron(today), lambda: check_repos(projects, today),
                  lambda: check_tasks(projects, today), lambda: check_voice_notes(today)):
        try:
            findings += check()
        except Exception as e:  # one broken check must not sink the brief
            findings.append(finding(f"ops:brief-check-error:{len(findings)}", "Operations", "high",
                                    "A Daily Brief check crashed", repr(e)[:200], acute=True))
    return findings


def main():
    ap = argparse.ArgumentParser(description="Daily Brief: what's slipping in the studio")
    ap.add_argument("--dry-run", action="store_true", help="print the note; no writes, no Slack")
    ap.add_argument("--no-notify", action="store_true", help="write the note but skip Slack")
    args = ap.parse_args()

    today = dt.date.today()
    findings = collect(today)
    try:
        state = json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        state = {}
    new_state = stamp_first_seen(findings, state, today)
    note, counts, top = render(findings, today)

    if args.dry_run:
        print(note)
        return

    out_dir = brief_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{today}-daily-brief.md"
    path.write_text(note)
    STATE_FILE.write_text(json.dumps(new_state, indent=2, sort_keys=True))
    print(f"{LOG_PREFIX} {dt.datetime.now():%Y-%m-%d %H:%M} wrote {path} "
          f"({counts['critical']} critical, {counts['high']} high, {counts['normal']} normal)")

    if args.no_notify:
        return
    from notifier import notify
    headline = "\n".join(f"• {'🔴' if f['severity'] == 'critical' else '🟠'} {f['title']}"
                         for f in top[:5] if f["severity"] != "normal") or "Nothing critical or high today."
    uri = obsidian_uri(path)
    link = f"<{uri}|Open the Daily Brief in Obsidian>" if uri else f"Note: {path}"
    ok = notify(f"{headline}\n\n{link}\n`{path}`",
                subject=f"Daily Brief: {counts['critical']} critical, {counts['high']} high, "
                        f"{counts['normal']} normal",
                priority="high" if counts["critical"] else "normal",
                sender="abderus", project="BSTD")
    if not ok:
        print(f"{LOG_PREFIX} Slack notify failed", file=sys.stderr)


if __name__ == "__main__":
    main()

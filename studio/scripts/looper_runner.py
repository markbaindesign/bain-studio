#!/usr/bin/env python3
"""Headless studio-looper runner.

Runs one or more looper windows unattended:

    python3 studio/scripts/looper_runner.py --now              # run immediately
    python3 studio/scripts/looper_runner.py --at 03:00         # run at 03:00
    python3 studio/scripts/looper_runner.py --now --at 03:00   # both, sequentially

Each window:
  1. Pre-syncs the SL project to completion (no tool timeouts involved), so the
     looper session's own sync is fast and can never be auto-backgrounded — the
     failure that silently killed the 2026-07-18 20:00 window.
  2. Launches `claude --dangerously-skip-permissions -p '/studio-looper --yes'`
     with stdout+stderr captured to ~/logs/studio-looper-run-{stamp}.log.
  3. Logs launch/exit (with exit code and a did-it-actually-work check) to
     ~/logs/studio-looper.log.

A lockfile prevents two runners racing. The runner exits after its last window:
nothing further is scheduled, so "stop when limit reached" is inherent — a run
that exhausts quota simply ends, and the runner moves on or exits.
"""

import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

STUDIO = Path("/media/data/dev/bain-studio")
LOG = Path.home() / "logs/studio-looper.log"
RUN_LOG_DIR = Path.home() / "logs"
LOCK = Path("/tmp/studio-looper/runner.lock")
TASK_LOG = Path.home() / "logs/task-looper.log"


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} RUNNER  {msg}\n")


def acquire_lock() -> bool:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        pid = LOCK.read_text().strip()
        if pid.isdigit() and Path(f"/proc/{pid}").exists():
            log(f"another runner is alive (pid {pid}) — refusing to start")
            return False
        log(f"clearing stale lock (pid {pid} dead)")
    LOCK.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    if LOCK.exists() and LOCK.read_text().strip() == str(os.getpid()):
        LOCK.unlink()


def sleep_until(hhmm: str) -> None:
    hh, mm = map(int, hhmm.split(":"))
    now = datetime.datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    delay = (target - now).total_seconds()
    log(f"sleeping {delay / 60:.0f}m until {target:%Y-%m-%d %H:%M}")
    time.sleep(delay)


def presync() -> bool:
    log("pre-syncing SL (blocking)")
    run_log = RUN_LOG_DIR / "studio-looper-presync.log"
    with run_log.open("a") as out:
        out.write(f"\n===== presync {datetime.datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
        out.flush()
        r = subprocess.run(
            [sys.executable, "studio/sync.py", "--project", "SL"],
            cwd=STUDIO, stdout=out, stderr=subprocess.STDOUT, timeout=1200,
        )
    log(f"pre-sync exited {r.returncode}")
    return r.returncode == 0


def task_log_size() -> int:
    return TASK_LOG.stat().st_size if TASK_LOG.exists() else 0


def notify(msg: str, priority: str = "normal") -> None:
    try:
        subprocess.run(
            [sys.executable, "studio/notifier.py", msg,
             "--priority", priority, "--sender", "studio-task-looper",
             "--project", "SL", "--channel", "looper"],
            cwd=STUDIO, timeout=60,
        )
    except Exception as e:
        log(f"notify failed: {e}")


def window_deadline() -> datetime.datetime:
    """Quota-window end: reset_ts from ratelimit-current.json.

    The file only refreshes when a claude session runs, so at the start of a
    window scheduled AT the reset time it still holds the boundary just passed
    — a stale (past) deadline killed the 2026-07-19 01:00 window after zero
    iterations. Sessions run in ~5h windows, so if the recorded reset is not
    comfortably in the future, assume a fresh window from now.
    """
    now = datetime.datetime.now()
    try:
        import json
        data = json.loads((Path.home() / ".claude/ratelimit-current.json").read_text())
        deadline = datetime.datetime.fromtimestamp(data["reset_ts"])
        if deadline > now + datetime.timedelta(minutes=10):
            return deadline
        log(f"recorded reset {deadline:%H:%M} is stale — assuming fresh 5h window")
    except Exception:
        pass
    return now + datetime.timedelta(hours=5)


def clear_orphan_state() -> None:
    # State files are disposable: the queue rebuilds from Looper Status in the
    # mirror/Asana. In -p mode the CLI exits after one result despite the Stop
    # hook's block decision, orphaning the file — clear it so the next
    # iteration's concurrency guard doesn't refuse to start.
    for f in Path("/tmp/studio-looper").glob("studio-looper.*.local.md"):
        f.unlink()
        log(f"cleared orphan state file {f.name}")


MAX_ITERATIONS = 30


def run_window(label: str) -> None:
    if not presync():
        log(f"window {label}: pre-sync FAILED — launching looper anyway (it re-syncs itself)")

    deadline = window_deadline()
    run_id = f"{datetime.datetime.now():%Y%m%d-%H%M}"
    log(f"window {label}: run id {run_id} — iterating until queue empty / no progress / {deadline:%H:%M}")
    tasks_done = 0

    for i in range(1, MAX_ITERATIONS + 1):
        if datetime.datetime.now() >= deadline:
            log(f"window {label}: deadline {deadline:%H:%M} reached after {i - 1} iterations")
            break

        clear_orphan_state()
        stamp = f"{datetime.datetime.now():%Y%m%d-%H%M%S}"
        run_log = RUN_LOG_DIR / f"studio-looper-run-{stamp}.log"
        before = task_log_size()
        log(f"window {label}: iteration {i} — output -> {run_log.name}")

        with run_log.open("w") as out:
            # Cheapest model works the task; advisor (sonnet) and one-shot
            # fable are the escalation rungs per the skill. LOOPER_RUN_ID keys
            # the shared review branch (one per window, not per iteration) and
            # arms the no-git-push PreToolUse hook.
            env = dict(os.environ, LOOPER_RUN_ID=run_id)
            r = subprocess.run(
                ["claude", "--dangerously-skip-permissions", "--model", "haiku",
                 "-p", "/studio-looper --yes"],
                cwd=STUDIO, stdout=out, stderr=subprocess.STDOUT, env=env,
            )

        if task_log_size() > before:
            tasks_done += 1
            log(f"window {label}: iteration {i} exited {r.returncode} — progress made")
        else:
            log(f"window {label}: iteration {i} exited {r.returncode} — NO progress "
                f"(queue empty or failure, see {run_log.name}) — ending window")
            break

    clear_orphan_state()
    log(f"window {label}: done — {tasks_done} productive iteration(s)")
    notify(
        f"looper window '{label}' finished: {tasks_done} productive iteration(s). "
        f"Details in ~/logs/studio-looper.log",
        priority="normal" if tasks_done else "high",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", action="store_true", help="run a window immediately")
    ap.add_argument("--at", action="append", default=[], metavar="HH:MM",
                    help="run a window at HH:MM (next occurrence); repeatable, run in order")
    args = ap.parse_args()

    if not args.now and not args.at:
        ap.error("nothing to do: pass --now and/or --at HH:MM")

    for hhmm in args.at:
        try:
            hh, mm = map(int, hhmm.split(":"))
            assert 0 <= hh <= 23 and 0 <= mm <= 59
        except (ValueError, AssertionError):
            ap.error(f"invalid time {hhmm!r} — expected HH:MM (00:00–23:59)")

    if not acquire_lock():
        sys.exit(1)
    try:
        if args.now:
            run_window("immediate")
        for hhmm in args.at:
            sleep_until(hhmm)
            run_window(hhmm)
        log("all windows done — runner exiting, nothing further scheduled")
        notify("looper runner done: all scheduled windows finished, nothing further scheduled.")
    finally:
        release_lock()


if __name__ == "__main__":
    main()

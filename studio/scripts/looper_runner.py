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


def run_window(label: str) -> None:
    if not presync():
        log(f"window {label}: pre-sync FAILED — launching looper anyway (it re-syncs itself)")

    stamp = f"{datetime.datetime.now():%Y%m%d-%H%M}"
    run_log = RUN_LOG_DIR / f"studio-looper-run-{stamp}.log"
    before = task_log_size()
    log(f"window {label}: launching headless looper — output -> {run_log.name}")

    with run_log.open("w") as out:
        r = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", "/studio-looper --yes"],
            cwd=STUDIO, stdout=out, stderr=subprocess.STDOUT,
        )

    worked = task_log_size() > before
    verdict = "task-looper.log grew (activity confirmed)" if worked else \
              "task-looper.log DID NOT GROW — run likely did nothing, check the run log"
    log(f"window {label}: looper exited {r.returncode} after run — {verdict}")


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
    finally:
        release_lock()


if __name__ == "__main__":
    main()

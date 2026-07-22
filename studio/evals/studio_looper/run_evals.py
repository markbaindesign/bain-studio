#!/usr/bin/env python3
"""Behavioral evals for the studio-looper skill (.claude/skills/studio-looper/SKILL.md).

studio/tests/test_looper_logic.py unit-tests the pure functions the skill calls into.
These evals are a different layer: they invoke the actual `claude -p '/studio-looper
--test ...'` CLI headless against the SLT sandbox project, to catch drift between what
SKILL.md *says* an agent should do (stop on a LIVE conflict, clear a STALE one and
proceed) and what a real invocation actually does when it reads the doc.

Not free like the unit tests — each scenario spends real tokens (one or more claude
invocations) and touches the real SLT Asana project via sync.py. That's fine: SLT exists
solely for this (see studio/looper-test/CLAUDE.md) and never touches SL or a client repo,
so these run as part of the normal pytest suite (studio/tests/test_looper_evals.py) —
no separate opt-in step. Run standalone when iterating on a single scenario:

    python3 studio/evals/studio_looper/run_evals.py                    # all scenarios
    python3 studio/evals/studio_looper/run_evals.py concurrency_live   # one scenario
    python3 studio/evals/studio_looper/run_evals.py --list             # list scenarios

Each scenario seeds /tmp/studio-looper state, invokes the skill under a timeout, asserts
on the resulting log lines / state files, then cleans up its own seeded state (the real
mirror mutations a scenario causes in SLT are left as-is — same as any other test run
against the sandbox).
"""

from __future__ import annotations

import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

STUDIO = Path("/media/data/dev/bain-studio")
STATE_DIR = Path("/tmp/studio-looper")
TASK_LOG = Path.home() / "logs/task-looper.log"
TARGET_PREFIX = "SLT"

sys.path.insert(0, str(STUDIO / "studio" / "scripts"))
from looper_logic import parse_state_frontmatter  # noqa: E402


def log_tail_marker() -> int:
    """Byte offset marking 'now' in task-looper.log, so we only inspect lines this
    scenario produced."""
    return TASK_LOG.stat().st_size if TASK_LOG.exists() else 0


def log_lines_since(marker: int) -> str:
    if not TASK_LOG.exists():
        return ""
    with TASK_LOG.open() as f:
        f.seek(marker)
        return f.read()


def clear_slt_state_files() -> None:
    """Remove every state file targeting SLT — real or fake, left over from a previous
    scenario or a run that got killed mid-flight. Scenarios must start from a clean slate:
    a genuine state file left behind by an earlier scenario's real work (e.g. the "stale"
    scenario proceeds to do actual work and writes its own session file) would otherwise
    look like a real LIVE conflict to the next scenario and fail it for the wrong reason."""
    for p in STATE_DIR.glob("studio-looper.*.local.md"):
        try:
            fm = parse_state_frontmatter(p.read_text())
        except OSError:
            continue
        if (fm.get("target_prefix") or "SL") == TARGET_PREFIX:
            p.unlink(missing_ok=True)


def write_state_file(session_id: str, current_task: str, deadline: datetime.datetime, mtime: datetime.datetime | None = None) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / f"studio-looper.{session_id}.local.md"
    path.write_text(f"""---
session_id: {session_id}
current_task: {current_task}
iteration: 0
max_iterations: 30
deadline: {deadline.isoformat()}
stop_at_pct:
target_prefix: {TARGET_PREFIX}
---
""")
    if mtime is not None:
        ts = mtime.timestamp()
        os.utime(path, (ts, ts))
    return path


def run_looper_headless(timeout_s: int = 90) -> tuple[int, str]:
    """Invoke the actual skill headless, same shape as studio/scripts/looper_runner.py."""
    try:
        r = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "--model", "haiku",
             "-p", "/studio-looper --test --yes"],
            cwd=STUDIO, capture_output=True, text=True, timeout=timeout_s,
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        def _s(x):
            if x is None:
                return ""
            return x.decode(errors="replace") if isinstance(x, bytes) else x
        return -1, _s(e.stdout) + _s(e.stderr)


class EvalResult:
    def __init__(self, name: str, passed: bool, detail: str):
        self.name, self.passed, self.detail = name, passed, detail

    def __str__(self):
        return f"[{'PASS' if self.passed else 'FAIL'}] {self.name} — {self.detail}"


# ---------------------------------------------------------------------------
# Scenario: a LIVE state file must block a second run outright
# ---------------------------------------------------------------------------

def eval_concurrency_live_blocks_second_run() -> EvalResult:
    name = "concurrency_live_blocks_second_run"
    fake_session = "eval-fake-live"
    fake_path = STATE_DIR / f"studio-looper.{fake_session}.local.md"
    marker = log_tail_marker()

    clear_slt_state_files()  # start clean — a leftover real file from another scenario would look like a genuine LIVE conflict
    write_state_file(
        session_id=fake_session,
        current_task="SLT-001",
        deadline=datetime.datetime.now() + datetime.timedelta(hours=1),
        mtime=datetime.datetime.now(),  # touched just now — clearly LIVE
    )

    try:
        _, output = run_looper_headless(timeout_s=180)
        still_there = fake_path.exists()
        other_state_files = [
            p for p in STATE_DIR.glob("studio-looper.*.local.md")
            if p.name != fake_path.name
        ]
        refused = "already running" in output.lower() or "not starting a second" in output.lower()

        if not still_there:
            return EvalResult(name, False, "the LIVE state file was deleted — guard rail says never delete another session's file")
        if other_state_files:
            return EvalResult(name, False, f"a new state file was created despite a LIVE conflict: {[p.name for p in other_state_files]}")
        if not refused:
            return EvalResult(name, False, f"no refusal language found in output (first 500 chars): {output[:500]!r}")
        return EvalResult(name, True, "LIVE file preserved, no second state file created, refusal message present")
    finally:
        # Real work never got a chance to start here (the whole point of this scenario is
        # that it's blocked at Step 1a), but clear anything anyway so the next scenario
        # starts clean.
        clear_slt_state_files()


# ---------------------------------------------------------------------------
# Scenario: a STALE state file (deadline passed) is cleared automatically and the
# run proceeds — no confirmation, no stopping.
# ---------------------------------------------------------------------------

def eval_concurrency_stale_cleared_and_proceeds() -> EvalResult:
    name = "concurrency_stale_cleared_and_proceeds"
    fake_session = "eval-fake-stale"
    fake_path = STATE_DIR / f"studio-looper.{fake_session}.local.md"
    marker = log_tail_marker()

    clear_slt_state_files()  # start clean
    write_state_file(
        session_id=fake_session,
        current_task="SLT-999-nonexistent",  # deliberately not a real task — must still be Queue-safe path taken
        deadline=datetime.datetime.now() - datetime.timedelta(minutes=1),  # already past
        mtime=datetime.datetime.now() - datetime.timedelta(minutes=20),
    )

    try:
        run_looper_headless(timeout_s=120)
        new_log = log_lines_since(marker)
        fake_gone = not fake_path.exists()
        # The agent's log wording varies run to run (sometimes it names the session_id,
        # sometimes it abbreviates) — don't assert on exact phrasing. What actually
        # matters: the file is gone (fake_gone) and it wasn't ever misclassified as a
        # live conflict (blocked_incorrectly). clear_slt_state_files() at scenario start
        # guarantees this was the only SLT state file present, so fake_gone alone already
        # proves it was this file that got cleared.
        cleared_logged = "Removed stale state file" in new_log or "stale" in new_log.lower()
        blocked_incorrectly = "already running" in new_log.lower()

        if blocked_incorrectly:
            return EvalResult(name, False, "run incorrectly refused on a STALE (expired) file instead of clearing it")
        if not fake_gone:
            return EvalResult(name, False, "STALE state file was never cleared")
        if not cleared_logged:
            return EvalResult(name, False, "state file vanished but no stale-clearing log line found — can't confirm it went through the documented path rather than some other deletion")
        return EvalResult(name, True, "STALE file cleared automatically, run proceeded without asking")
    finally:
        # This scenario's whole point is that the run proceeds past Step 1a and does real
        # work in SLT, which writes its OWN genuine session state file — clear everything
        # targeting SLT, not just the fake one, so the next scenario starts clean.
        clear_slt_state_files()


SCENARIOS = {
    "concurrency_live": eval_concurrency_live_blocks_second_run,
    "concurrency_stale": eval_concurrency_stale_cleared_and_proceeds,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", nargs="?", help="run one scenario by name (see --list)")
    ap.add_argument("--list", action="store_true", help="list scenario names and exit")
    args = ap.parse_args()

    if args.list:
        for k in SCENARIOS:
            print(k)
        return

    to_run = {args.scenario: SCENARIOS[args.scenario]} if args.scenario else SCENARIOS
    if args.scenario and args.scenario not in SCENARIOS:
        print(f"unknown scenario: {args.scenario!r}. Use --list to see options.", file=sys.stderr)
        sys.exit(2)

    results = []
    for scenario_name, fn in to_run.items():
        print(f"--- running {scenario_name} (this invokes claude headless, may take a minute) ---")
        start = time.time()
        result = fn()
        print(f"{result}  ({time.time() - start:.0f}s)")
        results.append(result)

    print()
    passed = sum(1 for r in results if r.passed)
    print(f"{passed}/{len(results)} scenarios passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()

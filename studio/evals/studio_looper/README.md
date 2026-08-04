# studio-looper evals

Two layers of testing for the studio-looper skill:

1. **Unit tests** — `studio/tests/test_looper_logic.py`, run via `pytest studio/tests/`.
   Fast, free, part of the normal test suite. Cover the pure functions in
   `studio/scripts/looper_logic.py` (concurrency classification, queue building/priority
   sort, orphan detection, deadline calculation) — the deterministic logic that used to
   be duplicated as inline Python heredocs inside SKILL.md and was never tested.

2. **Behavioral evals** — this directory. Invoke the actual skill headless
   (`claude -p '/studio-looper --test --yes'`) against the SLT sandbox project (see
   `studio/looper-test/CLAUDE.md`) to check that an agent reading SKILL.md actually
   behaves the way the doc says, not just that the extracted functions are correct in
   isolation. Costs real tokens and touches the real SLT Asana project — never run
   automatically, never part of CI.

## Running

```bash
python3 studio/evals/studio_looper/run_evals.py              # all scenarios
python3 studio/evals/studio_looper/run_evals.py concurrency_live
python3 studio/evals/studio_looper/run_evals.py --list
```

## Current scenarios

- `concurrency_live` — a LIVE state file (future deadline, recently touched) must block
  a second run outright: the original file is preserved, no second state file appears,
  and the session tells Mark it refused rather than racing the other run.
- `concurrency_stale` — a STALE state file (deadline already passed) must be cleared
  automatically with no confirmation, and the run must proceed rather than stopping.

## Adding a scenario

Each scenario is a function returning an `EvalResult`. Seed `/tmp/studio-looper/` state
via `write_state_file(...)`, call `run_looper_headless(timeout_s=...)`, assert on the
resulting state files / `~/logs/task-looper.log` lines, clean up any state you seeded in
a `finally` block, and register it in `SCENARIOS`.

Candidates not yet covered (need care to keep them cheap and side-effect-free in SLT):
- Duplicate-work guard: a task re-queued with no new Notes/comments after being marked
  Review should bounce straight back to Review with a note, not redo the work.
- Target routing guard: a task whose prefix doesn't resolve in `projects.json` should be
  marked Blocked, never guessed.
- Orphan recovery: a task stuck `In progress` with no live session gets reset to `Queue`
  (the `looper_logic.find_orphans` unit tests already cover the pure function — this
  would confirm the skill actually calls it and edits the mirror accordingly end-to-end).

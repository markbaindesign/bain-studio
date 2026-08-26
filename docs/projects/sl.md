---
tags:
- studio-project
prefix: SL
name: Studio Looper
status: active
client: Internal
type: internal
repo: (none — lives inside the bain-studio repo)
sector: Studio tooling
stack: Python · Claude Code
path: /media/data/dev/bain-studio/studio/looper
asana: "yes"
qa: "no"
inbox: "no"
open_tasks: 9
current_focus: Cross-project queue for unattended BainBot runs
next_action: "SL-127 — New Direct to U.S. Bank withdrawal fee starting Sept 2026"
---

# Studio Looper (SL)

Internal. The cross-project task queue BainBot works through on unattended runs. It is not a
codebase — the directory holds only a mirror, its sync state, and this project's `CLAUDE.md`.
Work itself always happens in the *home* project of each task, never here.

## How it differs from every other studio project

Most projects own their tasks. SL owns almost none of them: Mark multi-homes tasks from other
boards into it, so a task in SL is simultaneously a task in BD, PIPE, FOOB, and so on. Two
consequences follow, and both have bitten:

- **Every multi-homed task is mirrored twice** — once in its home project, once here — with a
  separate `asana-ids.json` for each. Any sync state that must be unique per *task* (rather than
  per project) cannot live in those files, because neither sync run can see the other's. This is
  what produced duplicate progress comments until the dedupe moved to Asana's own story list
  (2026-08-25).
- **`PRESERVE_FOREIGN_IDS: true`** — sync.py must not assign `SL-NNN` IDs to multi-homed tasks.
  They keep their home ID (`BD-152`, `PIPE-028`), which is how the looper routes each task to the
  right project directory. Only tasks *created* in SL get an SL ID.

## Looper Status

Workspace-level enum custom field driving the queue: `Queue` → `In Progress` → `Review` → `Done`,
with `Blocked` off to the side. Tasks arriving with no value are defaulted to `Queue` by sync.py.
BainBot hands finished work to Mark at `Review` rather than marking it `Done` itself.

## Key files

- `studio/looper/asana-mirror.md` — the queue, as mirrored
- `studio/looper/CLAUDE.md` — Asana wiring, status semantics, membership requirements
- `.claude/skills/studio-looper/SKILL.md` — the run procedure
- `studio/scripts/looper_logic.py` — concurrency classification (unit-tested)
- `studio/tests/test_looper_logic.py`, `test_looper_evals.py` — tests and behavioural evals

## Open tasks (active)

- SL-127 — New Direct to U.S. Bank withdrawal fee starting Sept 2026 (Queue)
- SL-129 — Bain design email not configured correctly (Queue)
- SL-126 — Follow up on job description gap analysis (Blocked)
- BD-152 — Performance audit (Blocked)
- BD-157 — Implement performance roadmap Phase 1 (Blocked)
- PIPE-056 — Follow up on RSS/remote job board poller (Blocked)
- PIPE-057 — Follow up on nudge priority proposals (Blocked)
- BSTD-768 — Audit Mark's own boilerplate for cross-project reuse (Blocked)
- FOOB-001 — Retire the remote demo site (Blocked)

12 further tasks sit in `Review` awaiting Mark's sign-off.

## Notes

- Asana project GID: `1216260498940192`
- bainbot must be a member of every home project too, or its tasks sync into SL unworkable —
  run `/looper-onboard {PREFIX}` when a project gains Asana wiring
- `studio/looper-test` (`SLT`) is a scratch board for testing looper changes safely
- Superseded `task-looper` per ADR 009

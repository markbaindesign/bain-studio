# ADR 017 — Per-client looper queues, bound to a client's own Claude account

Date: 2026-09-11
Status: Proposed
Related: [ADR 009](009-studio-looper-canonical.md) (studio-looper canonical), [ADR 014](014-ops-worktree-for-scheduled-jobs.md) (ops worktree)

## Context

Khyentse Foundation is billed on its own Claude account, reached through a separate config
directory (`~/.claude-kf`, pinned by an `.envrc` in the project root). The studio account
covers everything else.

The looper has no matching split. `SL` is a single cross-project queue — tasks from any of the
17 registered projects are multi-homed into it — and the queue is selected by exactly one flag
(`--test`, swapping `SL` for the `SLT` sandbox). So today KF work can be either:

- worked **interactively** under the KF account, billed correctly but needing a person; or
- worked **unattended** through `SL` under the studio account, which bills the studio for the
  client's work — and, worse, would bill the client for every other client's task if the run
  were simply started under `~/.claude-kf`.

Neither is right. The gap is not a filter; it is that a queue currently has no notion of which
account should pay for working it.

## Decision

Add a third queue, **`SLK` — Studio Looper (KF)** — following the existing `SLT` pattern
exactly, and bind each queue to the Claude account that should pay for it.

A queue is already a first-class thing in this architecture: a registered project directory
with its own Asana project, prefix, mirror and `asana-ids.json` (`studio/looper` → `SL`,
`studio/looper-test` → `SLT`). `SLK` adds `studio/looper-kf`. The new part is a per-queue
`CLAUDE_CONFIG_DIR`, so an unattended run of `SLK` executes on the KF account.

This is cheap because `(TARGET_PREFIX, TARGET_DIR)` is already a parameter almost everywhere:
`looper_logic.classify_concurrency()` skips state files whose `target_prefix` differs, so the
three queues get concurrency isolation for free, and Step 0 of the skill already demonstrates
swapping the pair.

## Implementation

### 1. Asana

Create project **Studio Looper (KF)**; add bainbot as a member; add the workspace-level
**Looper Status** enum field. Record the GID in `studio/looper-kf/CLAUDE.md`, then
`python3 studio/sync.py --setup --project SLK`.

### 2. Queue directory — `studio/looper-kf/`

`CLAUDE.md` modelled on `studio/looper/CLAUDE.md`:

```
ASANA_PROJECT_GID: <new>
ASANA_TASK_PREFIX: SLK
ASANA_PROJECT_NAME: Studio Looper (KF)

PRESERVE_FOREIGN_IDS: true
```

`PRESERVE_FOREIGN_IDS: true` matters for the same reason it does on `SL`: multi-homed tasks keep
their home ID (`KF-WEB-185`), which is how the skill routes work to `/media/data/dev/vvv/clients/www/kf-21`.

### 3. Register the queue

Add to `studio/projects.json`:

```json
{ "path": "/media/data/dev/bain-studio/studio/looper-kf", "status": "active" }
```

### 4. Skill — `--kf` flag

In Step 0, alongside `--test`: `--kf` sets `TARGET_PREFIX=SLK` and `TARGET_DIR=studio/looper-kf`.
Mutually exclusive with `--test` (error if both). Every existing `{TARGET_PREFIX}` / `{TARGET_DIR}`
reference then resolves correctly with no further edits, and log lines tag `[SLK]`.

### 5. Client-only guard (Step 2)

After building the queue, **refuse any task whose ID prefix is not `KF-WEB`** — log it, skip it,
carry on. This is the entire point of the split: one stray non-KF task in the queue silently bills
the client. Cheap to enforce, and it fails safe. Same rule shape as "never queue a completed task".

### 6. Account binding — the substantive work

**a. `~/.claude-kf` needs the looper machinery.** It currently has no hooks and no skills
directory, so the Stop hook never fires and `/studio-looper` is not invocable. Add to
`~/.claude-kf/settings.json`, by absolute path exactly as the studio config does:

- `Stop` → `studio-task-looper-stop-hook.sh`
- `PreToolUse` `Write|Edit` → `looper-concurrency-guard.sh`
- `PreToolUse` `Bash` → `looper-concurrency-guard.sh`, `looper-no-push.sh`

and `ln -s ~/.claude/skills ~/.claude-kf/skills`.

The two guards are not optional: the concurrency guard exists because an eval caught a headless
haiku run clearing a genuinely live state file (2026-07-22), and `looper-no-push.sh` is what keeps
an unattended run off shared branches per ADR 009.

**b. The quota file must follow the account.** Five call sites hardcode
`~/.claude/ratelimit-current.json` — the studio account's snapshot:

| Site | Purpose |
|---|---|
| `SKILL.md` Step 0 (`--use N%`) | stop threshold |
| `SKILL.md` Step 1c | headroom log |
| `SKILL.md` Step 2 | deadline (quota reset) |
| `SKILL.md` Step 4e | per-iteration spent check |
| `looper_runner.py:190` | quota-window end |

Each must resolve `$CLAUDE_CONFIG_DIR` with `~/.claude` as fallback, mirroring the fix already
applied to `~/.claude/hooks/statusline.py` (which writes the file). Without this an `SLK` run
budgets itself against the studio account's remaining quota — wrong in both directions, and
invisible until a window overruns. `save-ratelimit.sh` carries the same hardcode; it is currently
unwired, but fix it in the same pass.

### 7. Runner — `looper_runner.py`

Hardcodes `SL` in four places: the pre-sync (`--project SL`), the mirror path
(`studio/looper/asana-mirror.md`), the notifier call (`--project SL --channel looper`), and the
session invocation (`-p '/studio-looper --yes'`).

Add `--queue {sl|slt|slk}` (default `sl`) resolving one table:

```python
QUEUES = {
    "sl":  {"prefix": "SL",  "dir": "studio/looper",      "flag": "",        "config_dir": None},
    "slt": {"prefix": "SLT", "dir": "studio/looper-test",  "flag": " --test", "config_dir": None},
    "slk": {"prefix": "SLK", "dir": "studio/looper-kf",    "flag": " --kf",   "config_dir": "~/.claude-kf"},
}
```

The account binding is one line, at the existing env hook point:

```python
env = dict(os.environ, LOOPER_RUN_ID=run_id)
if q["config_dir"]:
    env["CLAUDE_CONFIG_DIR"] = os.path.expanduser(q["config_dir"])
```

Run logs should carry the queue in their filename so two windows' logs don't interleave.

### 8. Cron

A second window from the ops worktree (ADR 014 — so this ships by deploying the worktree, not
merely by committing):

```
30 2 * * * cd /home/bain/ops/bain-studio && python3 studio/scripts/looper_runner.py --now --queue slk >> $HOME/logs/studio-looper-kf-cron.log 2>&1
```

30 minutes after the `SL` window, so the two never contend. They are separate accounts, so there
is no shared quota to exhaust — only machine contention.

### 9. Before first unattended run

`/studio-looper --kf --health-check`, then a `--dry-run`, then one supervised `--for 30m`.
Extend `studio/tests/test_looper_logic.py` with a three-prefix concurrency case.

## Consequences

- KF's unattended work is billed to KF; the studio's to the studio. The guard in §5 makes
  mis-billing a logged skip rather than a silent charge.
- Queue count grows to three; adding a fourth client later is now a config exercise
  (directory + Asana project + `QUEUES` row), not a redesign.
- Two cron windows and two run-log streams to watch.
- `~/.claude-kf` gains hooks, so it stops being a thin interactive config and needs keeping in
  step with the studio config. The skills symlink means skills themselves stay single-sourced.

## Alternatives considered

**Filter `SL` by prefix at run time under the KF account.** Rejected: the mirror, the sync, the
notifications and the run log all stay studio-scoped, and correctness depends on a filter holding
on every iteration. One missed task bills the client for another client's work.

**Leave it as is — KF unattended work billed to the studio.** Viable while the volume is low, and
the honest fallback if the queue would rarely be non-empty. The cost of this ADR is only worth
paying if KF tasks are actually queued regularly.

## Open questions

- Slack: its own channel, or `looper` with the `[SLK]` tag doing the work?
- Does anything else need to follow the account split — Harvest time entries, notification
  routing — or is compute billing the whole of it?

# ADR 007 — Task looper logging

**Date:** 2026-06-25
**Status:** Accepted

## Decision

The task-looper skill writes a persistent log to `~/logs/task-looper.log` using inline `echo` appends at each loggable event.

Format matches `studio/sync.log`:

```
YYYY-MM-DD HH:MM:SS INFO    [PREFIX] message
```

The `[PREFIX]` tag (e.g. `[BD]`, `[WTF]`) makes individual project runs greppable:

```bash
grep "\[BD\]" ~/logs/task-looper.log
```

What gets logged: session start/end, task lifecycle (started/complete/blocked with reason), git ops (branch, commits, push, PR URL), sync.py calls, notifier.py calls, non-zero exit errors (command + stderr).

No log rotation. A review task is scheduled for 2026-07-09 to check file size and decide if rotation is needed.

## Context

The task-looper runs autonomously without supervision. When it stops unexpectedly there is no record of what it did or why. Debugging requires re-reading mirror files and git history - slow and incomplete.

## Consequences

- Post-session debugging is possible without reading git history or mirror diffs
- Log lives at home-dir level, not in the studio repo - not version-controlled
- File will grow indefinitely until rotation policy is decided (ADR-008 if rotation is adopted)
- Inline `echo` chosen over a Python helper script for token efficiency

---

*See also ADR-008 (not yet written) if log rotation is adopted.*

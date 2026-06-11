# Studio Shutdown

End-of-session routine. Commits mirror edits, captures learnings, flags unfinished work, and leaves the studio clean. Run at the end of every work session.

## Invoke

```
/studio-shutdown
```

## What it does

1. **Check for unsaved mirror edits** — scans each active project for uncommitted changes to `.claude/asana-mirror.md`; pushes any changes to Asana via `sync.py --project {PREFIX}`
2. **Check for open feature branches** — reports branches with completed work but no PR
3. **Run the session retro** — invokes `/studio-retro` to capture what was done, what was learned, and what's left open
4. **Flag dangling work** — any in-progress tasks that weren't completed are listed explicitly so nothing is silently dropped

## Output

- Sync confirmation per project (or a warning if any project failed to sync)
- Open branch list with PR status
- Session retro notes
- List of tasks to pick up next session

## Notes

- Do not skip this at the end of a session — unsaved mirror edits accumulate quickly and cause drift between local state and Asana
- Pairs with `/studio-startup` which opens the session loop

## See also

- [sync.md](sync.md) — the underlying Asana sync
- [studio-startup.md](studio-startup.md) — the opening counterpart

---
tags: [utility, security, hooks]
god: periphetes
command: studio/scripts/setup-machine.sh
description: Commit hooks that refuse client data in this public repo, with the term list generated from the registry outside it.
---

# client-guard

Two git hooks refuse a commit that would publish client identity:

| Hook | Checks |
|---|---|
| `studio/hooks/pre-commit` | the lines this commit **adds** |
| `studio/hooks/commit-msg` | the commit **message** |

Install once per clone:

```bash
studio/scripts/setup-machine.sh
```

It sets `core.hooksPath=studio/hooks` and reports whether this machine can
actually build a denylist. `core.hooksPath` is per-clone, so a second checkout
needs it too.

## Four decisions that make it work

**The term list is never committed.** It is generated at commit time by
[gen-denylist](gen-denylist.md) from the registry outside this repo. A list of
client names, committed so a hook could grep for it, would be the exact data the
hook exists to exclude.

**Added lines only.** `pre-commit` reads `git diff --cached -U0` and looks at
`+` lines. A whole-diff match would refuse the commits that *remove* client
data — including every commit of the migration that introduced this guard.

**The message is checked separately.** `pre-commit` never sees the commit
message, and the studio's own rules deliberately send reasoning into commit
messages, which are public.

**No registry means refuse, not pass.** If the registry is missing, unreadable
or holds no client entries, both hooks exit non-zero and say how to fix it. An
empty denylist would let everything through while appearing to work, and the
machine without a registry is the unconfigured one where that matters most.

## Getting past it

```bash
BAIN_SKIP_CLIENT_GUARD=1 git commit ...
```

Documented rather than hidden, because `--no-verify` bypasses any pre-commit
hook anyway. An undocumented escape gets found in a hurry, at the worst moment.

## What it allows

Project prefixes — `KF-WEB`, `TSTY`, `EBIZG`. A prefix is a code, and the
mapping to a client lives outside this repo. Prefixes are never in the denylist,
and without that rule the list matched 46 files on a task ID.

`CHANGELOG.md` is skipped. Past release entries stay as written, since the
identical text is in `git log` either way; new entries use prefixes by rule
rather than by enforcement.

## Checking the whole tree

The hooks only see a commit. For the current tree:

```bash
git grep -lIiwF -f <(python3 studio/scripts/gen-denylist.py) -- . ':!CHANGELOG.md'
```

Nothing is the expected answer.

## The limit worth knowing

**The guard is exactly as complete as the registry.** It cannot catch a client,
domain or install name nobody recorded. Three separate sweeps of this repo each
found identifiers the previous denylist had no idea existed. That is why
`/register-project` insists on `domains` and `kind`, and why
[gen-denylist](gen-denylist.md) carries the discovery commands for finding what
the registry is missing.

## Related

- [gen-denylist](gen-denylist.md) — builds the term list
- [registry](registry.md) — where identity lives
- [ADR 021](../adr/021-studio-state-and-registry-leave-the-repo.md) — why, and the 2026-11-06 addendum
- [ADR 026](../adr/026-one-session-per-checkout.md) — enforcement is a hook, not a rule
- `~/.claude/rules/no-client-data-in-public-repos.md` — the rule across all three public repos

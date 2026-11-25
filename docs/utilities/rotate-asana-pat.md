---
tags: [utility, security, asana]
god: periphetes
command: studio/scripts/rotate-asana-pat.sh
description: Rotate the bainbot Asana PAT across every live location at once, prove it against the API first, and clear the stale credential backups.
---

# rotate-asana-pat

The bainbot token is held in three separate live files. Rotating by hand means
missing one and finding out hours later, when a scheduled sync fails quietly.

```bash
studio/scripts/rotate-asana-pat.sh --check    # where the current token lives
studio/scripts/rotate-asana-pat.sh            # rotate
```

## Run it in your own terminal, not in a Claude session

Anything typed at a session prompt is written to that session's transcript.
That is not a precaution in the abstract: the token this script exists to
replace reached nine lines of `~/.claude/history.jsonl`, five session
transcripts, two editor-history files and a `MEMORY.md` precisely because it
travelled through those channels (BSTD-865).

So the script takes the new token from `read -rs` only — never an argument,
which would land in shell history — never echoes it, and runs with `set +x`.

## What it touches

| File | Why it holds the token |
|---|---|
| `studio/.env` | `ASANA_PAT`; the symlink layout means every worktree and the ops checkout pick it up at once |
| `~/.claude/settings.json` | `env.ASANA_TOKEN`, injected into every session |
| `~/.claude-kf/settings.json` | the same, for the second account |

It then offers to delete `settings.json.bak*` in both directories. Those are
superseded backups holding a dead credential, and a backup of a credential
file is how the spread began.

## Order of operations

1. Reads the current token from `studio/.env` to build the search literal —
   nothing about the token is in this repo, which is public.
2. Reports the before state, one count per target.
3. Prompts for the new token and checks its shape.
4. **Calls `GET /users/me` with it before writing anything.** A half-rotated
   set of files carrying a bad token is worse than not having started.
5. Replaces it in each target, in place, with no `.bak`.
6. `chmod 600` on each — they were mode 664.
7. Deletes the stale backups, on confirmation.
8. Re-reports: old token 0 everywhere, new token once each.

Copies in transcripts, shell history and editor history are left alone. They
cannot be scrubbed reliably, and rotation is what makes them harmless.

## Left deliberately undone

- Revoking the old token is yours to do in the Asana UI, and the script says
  so at the end. Until it is revoked, every dead copy on disk still works.
- Asana's token page shows neither an id nor a creation date, so you cannot
  tell two PATs apart by looking. The script asks `/users/me` and prints the
  name, email and gid before writing anything — that is the only reliable way
  to know which account a token belongs to, and it catches the common slip of
  generating one on the human account instead of the bot's.
- Whether the two `settings.json` files should hold a token at all is
  BSTD-814. An `env` entry there loads into every session's context, which is
  the mechanism behind most of the spread.

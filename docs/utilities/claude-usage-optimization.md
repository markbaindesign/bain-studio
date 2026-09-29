---
tags:
- reference
- guide
description: How to work with Claude without burning the weekly quota — model choice,
  session hygiene, and what actually costs tokens
---

# Claude usage optimization

Written 2026-09-18, after two days of heavy studio work (looper build-out, Daily Brief,
audio notes, uptime monitoring) burned 68% of a weekly quota by Thursday. Not a one-off:
this is the recurring failure mode, and the fix is a small number of concrete habits, not
a philosophy.

## What actually costs quota

In order of effect:

1. **Model choice, per task.** Opus is the most expensive model per token. Running it for
   routine work — file edits, greps, test runs, doc writing, mirror updates — is the single
   biggest lever available. Sonnet handles nearly all of that at a fraction of the cost.
2. **Session length.** Every turn re-sends the *entire* conversation so far. A session that
   has covered six unrelated topics by hour four costs far more per message than the same
   conversation would have cost split into six short sessions — even though the total work
   done is identical. Cost grows with accumulated context, not with wall-clock time.
3. **Wide sweeps that dump a lot into context.** Reading every project mirror, running a
   full test suite repeatedly, or a browser pass over ten pages all feed a lot of text back
   into the conversation. That text then travels with every later turn in the same session,
   not just the one that fetched it.
4. **Subagents.** Each spawned agent starts its own context and re-derives what the parent
   already knows. Only worth it for genuinely parallel, independent work — never as a
   default.

What does **not** cost extra: voice input. Dictation is transcribed to text (via Whisper,
billed separately and trivially, ~$0.006/minute) before it reaches Claude — a spoken
instruction costs what the same typed instruction costs. The only wrinkle is that spoken
phrasing tends to run longer than typed phrasing for the same content.

## Rules, in priority order

1. **Switch model per task, not per session.** `/model sonnet` for edits, tests, research,
   docs, mirror updates — anything routine. `/model opus` only for architecture decisions,
   hard debugging, or design review. Switch back afterward. This is the rule that matters
   most; everything else is secondary to it.
2. **One topic per session, then `/clear`.** If the conversation is moving to an unrelated
   piece of work, clear first. A session that drifts across five topics pays the accumulated-
   context cost on every one of them, in a way five separate sessions would not.
3. **Prefer scheduled/cron work over asking Claude to do it live.** Anything that can run
   as a deterministic script on a schedule (collectors, the Daily Brief, the audio-notes
   sweep) costs no model quota to run and no quota to read the output the next morning.
   Studio tooling favors this by default — see the "Tooling design" rule in the global
   CLAUDE.md.
4. **Ask for targeted runs, not full ones.** "Run the test for the file I changed" instead
   of "run the whole suite" mid-task; a full run is for before a commit, not after every edit.
5. **Don't spawn subagents by default.** Only for genuinely independent, parallelizable
   work — never as a way to "save" the parent session's context, since the total cost is
   additive, not saved.
6. **The looper spends from the same quota.** A nightly `studio-looper` run works through
   whatever is in Queue using the invoking account's quota, same as an interactive session.
   Queue a handful of tightly-scoped tasks, not the full backlog, on a week that's already
   tight — or leave the queue empty and let the run finish immediately at near-zero cost.

## Checking where you stand

`/usage` in the CLI is the only way to see the actual remaining percentage — nothing else
in this repo or the studio dashboard tracks it today. `studio-looper` logs a rough usage
reading at the start of each run (`~/logs/task-looper.log`), which is useful as a signal but
is not a substitute for checking `/usage` directly before planning a day's work.

**Idea not yet built:** BSTD-021 (API cost tracker on the studio dashboard) would close this
gap for querying/visualizing use, though `/usage` is still the source of truth for what's
left on the plan this week.

## A concrete week

- **Conserve (default posture on a tight week):** Sonnet for everything, Opus only when
  actually stuck; short single-topic sessions with `/clear` between; nightly looper queue
  capped at 2-3 small tasks or left empty; anything not requiring Claude goes to the manual
  tasks list instead of being asked of an agent.
- **One focused build:** pick a single piece of work, spend a deliberate Opus session on it,
  leave everything else for after the weekly reset.
- **Spend it down:** the default failure mode described above — long Opus sessions across
  many topics, full nightly looper queues. Burns a week's quota in two or three days.

## Related

- [notifier.md](notifier.md), [daily-brief.md](../gods/hermes/daily-brief.md),
  [audio-notes.md](../gods/hermes/audio-notes.md) — scheduled work that costs no live quota
- Global CLAUDE.md, "Tooling design" — prefer deterministic scripting over live agent work
  for anything repeatable

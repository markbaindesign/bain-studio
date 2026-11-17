# ADR 025 — Task descriptions are read-only and short; custom fields push back

Date: 2026-11-05
Status: Accepted (2026-11-05)
Related: [ADR 022](022-asana-tasks-carry-their-own-context.md), [sync.py](../gods/hermes/sync.md), [new-task](../utilities/new-task.md), [asana-comments](../utilities/asana-comments.md)

## Context

Two problems in the same field.

**Descriptions had become essays.** Agent-created tasks were running 2,000–3,500 characters
against a studio median of about 500: BSTD-775, -807, -866, -868 and -856, the last with a
"Why it matters now" section recounting how the problem arose. The same failure had already
been fixed for comments, where `validate_progress_note` refuses a wall of text outright
rather than warning about it. Descriptions had no such limit, and no rule saying what belongs
in one.

**Most fields could not be edited in the mirror.** `sync.py` pushed due date, start date,
assignee, assignee status, section, tags, followers, dependencies and Looper Status. Priority
was read into the mirror and rendered, but there was no push path for it, so an edit to
`- **Priority:**` was silently discarded and overwritten on the next pull. Other custom
fields — Features, Review Status, Env, Milestone — were not mirrored at all. The only enum
with a push path was Looper Status, which had been added for the queue.

The description is also the one genuinely multi-line field, and `FIELD_RE` is not DOTALL, so
the mirror parser only ever captured its first line. That is why it was excluded in the first
place.

## Decision

1. **Every custom field on a task is mirrored**, by its Asana name, rendering `none` when
   unset. Handling is generic: a field added to a project in Asana appears in the mirror and
   is pushable with no change to `sync.py`.
2. **Five custom field types push back** — text, number, date, enum, multi-enum. Anything
   Asana computes or holds in a shape one mirror line cannot express (people, formula,
   reference) is mirrored from its `display_value` and left read-only.
3. **A value the field cannot hold is never sent.** It is skipped and named in the log. Asana
   rejects the whole write, so one bad value in a batch would otherwise lose every other
   field pushed with it.
4. **A multi-enum push writes exactly the set the mirror shows**, replacing what Asana held.
   A mirror that does not mean "this is the whole value" is not a mirror.
5. **The task description stays read-only in the mirror.** It is the brief the task was
   created with. Amendments go in a comment; a genuinely wrong description is rewritten with
   `--update-task`, which logs the change. A mirror-side edit is reported in the log, naming
   the command, rather than silently dropped.
6. **A description written through `sync.py` is refused over 1,200 characters** on creation,
   with nothing sent to Asana. On `--update-task` an over-limit description is refused only
   when it is no shorter than the one it replaces: 21 existing studio descriptions are already
   over the limit, and refusing a shorter correction to one of them would leave the misleading
   text in place. The limit is on length only — no block format
   is required, so tools with their own templates (`qa-capture`) keep working. What belongs in
   a description, and what does not, is a rule rather than a parser:
   `~/.claude/rules/asana-tasks.md`.

## Consequences

- Mirrors carry a few more lines per task. On BSTD that is four (`Env`, `Review Status`,
  `Features`, `Milestone`), most of them `none`. That is the cost of the `none` line being
  the thing you edit to set a field.
- Setting Priority is now a mirror edit plus a sync, rather than a trip to the Asana UI.
- The description is deliberately the one field with an asymmetry: mirrored in full, pushed
  never. Anyone looking for consistency will find this inconsistent; the reason is that a
  description is a record of what was asked for, and Asana keeps no history of its own.
- The task title and completion still do not push from the mirror. A title is changed with
  `--update-task --task-name`; a task is completed in Asana. Only the description, the title
  and completion are outside the mirror's push, and the docs name all three rather than
  claiming "everything else pushes".
- A description's own text is no longer collected as fields. It routinely contains bold
  bullets of its own, and because every field landed in one map where the last match won, a
  `- **Priority:** none` line inside a description replaced the real value and was then pushed
  to Asana. Descriptions can arrive by email, which CLAUDE.md treats as untrusted, so this was
  a write path from untrusted text into task state.
- Long inbound material is unaffected. Tasks created by Asana's email intake never pass
  through `sync.py`, so a forwarded alert keeps its full text (BSTD-038, -821, -834).
- `paste_job.py` has its own Asana pipeline and is not covered by the limit. If it is ever
  moved onto `sync.py`, its generated proposal needs somewhere else to live.

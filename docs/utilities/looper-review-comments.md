---
tags: [utility, reference]
god: hermes
command: python3 studio/sync.py --project {PREFIX}
description: How the looper reports finished work in Asana — the review note template, the @mark mention signal, and the one-task-one-comment rule
---

# Looper review comments

How finished looper work reaches Mark in Asana. Replaces the free-form progress notes that
produced unscannable walls of text.

## The problem it fixes

A completed task used to collect three or more comments: one from the queue mirror, one from
the home project mirror, and any corrections. Each was a paragraph of narrative — diagnosis,
what was ruled out, every width tested — with the thing Mark actually had to *do* buried in
it or absent. Asana truncates at "See more", so the action was often invisible.

## How a note becomes a comment

`**Progress:**` is **not an Asana field.** It is mirror-local: `parse_existing_mirror`
carries it between runs and it is never pulled from Asana. Its only purpose is to be turned
into a comment by `sync_project` and then forgotten.

That means **two mirror files are two independent write channels into one Asana task's
comment thread.** A multi-homed task (home project + looper queue) is synced once per
project, each with its own state file, so the second sync has no record of the first having
commented. The dedupe in `sync.py` compares comment text, so it only catches *identical*
notes — and the looper wrote deliberately different text to each mirror, which defeated it.

**The rule: the Progress note is written in the home project mirror only.** The queue mirror
carries `Looper Status` and `Assignee` and nothing else.

## The template

One mirror line. `FIELD_RE` is not DOTALL, so a literal newline truncates the note and a
continuation line starting `- **X:**` is misparsed as another field. `||` separates blocks
and is expanded to newlines at post time by `_progress_plain`.

```
**Progress:** @mark Review {YYYY-MM-DD}: {what changed, one line} || Where: {branch} · {commits} · {URL or path} || Check: || 1. {imperative} || 2. {imperative} || Gaps: {known, not fixed}
```

| Block | Holds | Limit |
|---|---|---|
| `Review {date}:` / `Blocked {date}:` | What changed, or the question | One line, ISO date required — the looper's duplicate-work guard reads it to tell a completed task from a re-queued one. Asana truncates at "See more", so the action lives here or nowhere. |
| `Where:` | Branch, commits, URL or file path | One line. For a research task, the output file path instead. |
| `Check:` | What Mark does to verify | Max 5, one line each, imperative. More than 5 means the task should have been split. |
| `Gaps:` | Work knowingly left undone | Omit entirely when there is none. Never a hedge. |

**No reasoning, no diagnosis, no alternatives considered, no session-usage line.** The
reasoning goes in the looper commit message, reachable by `git log looper/{session}` when
Mark wants it and invisible when he does not. Usage is already in
`~/logs/task-looper.log`.

## The @mark mention is the signal

Mark's Asana inbox is filtered to **Mentioned**. A plain-text comment cannot mention anyone —
Asana needs rich text (`html_text`) carrying `<a data-asana-gid="…"/>`. So:

- A note opening `@mark` is posted with a real mention and reaches his inbox.
- A note without the token is posted and recorded, but he never sees it.

This is the whole signalling mechanism, and it is why `sync.py` must never add the mention
unconditionally. Use the token for **review** and **blocked** notes — the two cases where
Mark must act. Never for routine status changes. A low-risk fix stays off his radar without
anything being hidden: it is on the task, it just does not interrupt him.

`_render_progress` also HTML-escapes the body. Asana returns a 400 on a bare `&`, `<` or
`>`, and notes routinely contain `&`, `<1000px` and `->`.

## Corrections edit in place

`leave_progress_comment` edits bainbot's existing comment (`PUT /stories/{gid}`) rather than
posting a second one, so the thread holds one current note instead of a note plus a
contradiction. A "Correction …, replacing my earlier note" comment is a defect.

The decision is made in `sync_project`:

| Situation | Action | Why |
|---|---|---|
| No human comment since our last note | **Edit** the existing comment | Same work, better note. No second notification. |
| A human comment landed after it | **Post** a new comment | Mark responded — a rejection or a question — so this is a new round of work and needs its own notification. |

If the edit fails (403/404 — comment deleted, or authored by someone else) it falls back to a
fresh post rather than losing the note.

Story GIDs live in their **own** `progress_stories` map in the project's `asana-ids.json`,
never inside `posted_progress`. The hourly cron runs an older `sync.py` from the ops worktree
(ADR 014) against the same state file, and it reads `posted_progress[gid]` as a plain string:
a dict there made its `curr_p != posted_progress[gid]` test true on every run, so it posted
the note a second time as raw text — literal `@mark` and `||` — and overwrote the GID. A
project whose state predates this change simply has no `progress_stories` entry, so its first
note posts fresh instead of editing.

## Matching a comment to its note

`_comment_matches` compares by **suffix**, not equality. Asana renders a mention as the
user's display name, so a posted comment never again equals the mirror text that produced it.
Stripping the name by pattern was tried and ate real words after it
(`@[\w .'-]+` matched "Mark Bain Review"); the mention is only ever a prefix, so a suffix
test needs no name parsing and still matches a note posted without one exactly.

## Approval and rejection

- **Approve:** Mark completes the task. The looper never marks a task done — that judgement
  and that click are his.
- **Reject:** he comments on the task and sets `Looper Status` back to `Queue`. The
  duplicate-work guard in the looper skill already treats a comment dated after completion
  as "re-work needed", and the next note posts fresh rather than editing.

## Not built

- **Screenshot attachments.** `sync.py` downloads attachments (`fetch_task_attachments`) but
  cannot upload. Asana takes a multipart `POST /attachments`; a visual check ("the header at
  720px") would read better as one image than as sixty words. Deferred, not rejected. If it
  is built, it needs a two-image ceiling and must skip re-downloading bainbot's own uploads,
  since `.png` is in `ATTACHMENT_EXTS`.
- **Silent auto-close for low-risk fixes.** Considered and dropped: everything goes to review
  for now. The mention filter already keeps routine notes off Mark's radar without Claude
  having to judge its own risk.
- **The other three Progress writers** — `studio-delivery-gate`, `feature`, `end-session` —
  still write free-form notes. They inherit the `sync.py` plumbing (mention support,
  edit-in-place) but not the template, because "finished a build, needs review" is not their
  shape. They post without a mention, so they are now silent in a filtered inbox.

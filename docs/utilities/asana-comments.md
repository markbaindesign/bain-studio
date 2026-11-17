---
tags: [utility, reference]
god: hermes
command: python3 studio/sync.py --project {PREFIX}
description: How Claude comments on an Asana task from any project — the note template, the @mark signal and what it really does, and the one-task-one-comment rule
---

# Asana comments

How any Claude session comments on an Asana task. **Not a looper rule** — the wall-of-text
comment that prompted this came from an ordinary bain.design session. The global rule that
every session loads is `~/.claude/rules/asana-comments.md`; this is the reference behind it.

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
**Progress:** @mark Review: {what changed, one line} || Check: || 1. {imperative} || 2. {imperative} || Gaps: {known, not fixed} || Where: {branch} · {commits} · {URL or path}
```

`split_location` pulls every `Where:` block out of the note. `post_note` posts the rest as the
summary (with the `@mark` mention), then the `Where:` block as a separate silent comment under
it. Its story GID is kept in the state file's `progress_where_stories`; it is edited in place
when the summary is, and skipped when an identical bainbot comment is already on the task. With
`--comment`, pass `--where-story-gid` alongside `--story-gid` to correct both.

An `@mark` summary may not contain a URL, git-flow branch, path, file name or commit SHA
(`LOCATION_RE`): those are what Mark looks up, not what he reads to decide.

| Block | Holds | Limit |
|---|---|---|
| `Review:` / `Blocked:` / `Done:` | What changed, the question, or the outcome | One line, no date: Asana stamps the comment, and the looper's duplicate-work guard reads that stamp. Asana truncates at "See more", so the action lives here or nowhere. |
| `Check:` | What Mark does to verify | Max 3, one short line each, imperative, no locations. More means the task should have been split. |
| `Gaps:` | Work knowingly left undone | Omit entirely when there is none. Never a hedge. Anything meant to be done later is a task, cited by ID. |
| `Subtasks:` | Each open subtask: done, or why not needed | Required on a `Done` note while subtasks are open (`validate_done_subtasks`). |
| `Where:` | Branch, commits, URL or file path | Its own silent comment. For a research or decision task, the file the output or decision is recorded in. Max 300 chars. |

Limits on the summary: 500 chars, 150 per block, 6 blocks. A `Done` note on a task with open
subtasks and no `Subtasks:` block is refused, read live via `open_subtask_names`. A decision task
is done only once the decision is written into a project doc and that file is named in `Where:`.

**A follow-up is a task, not a sentence.** Before a comment names further work — a follow-up,
a next step, a `Gaps:` item that someone is meant to pick up — create it with
`sync.py --create-task --follow-up-of {this task's ID}` and cite its local ID. Work mentioned only in a comment is lost.

**Cite related tasks by local ID** (`BSTD-856`). `sync.py` turns every ID that resolves in a
registered project's `asana-ids.json` into a link to that task, so Mark can jump to it. Write
the bare ID: no URL, no GID, no task title.

**No date in the note.** Asana stamps every comment; write `Review:` and `Blocked:`, not
`Review 2026-11-05:`.

### How a task ID becomes a link

`_render_progress` wraps each local ID that resolves through `_local_id_maps()` in
`<a data-asana-gid="{gid}" data-asana-dynamic="false">{ID}</a>`. The `dynamic="false"` keeps
the ID as the link text: without it Asana turns any task link, `href` or `data-asana-gid`,
into a mention showing the task's title. An ID inside a branch name, path or URL
(`feature/BSTD-878-x`) and an ID that resolves nowhere stay plain text.

Asana stores a linked ID in the story's plain `text` as `https://app.asana.com/0/0/{gid}/f/`,
so `_comment_matches` maps those URLs back to IDs before comparing. Validation runs on the
mirror text, so link markup never counts against the limits. Verified against SLT-001 on
2026-11-17.

**No reasoning, no diagnosis, no alternatives considered, no session-usage line.** The
reasoning goes in the looper commit message, reachable by `git log looper/{session}` when
Mark wants it and invisible when he does not. Usage is already in
`~/logs/task-looper.log`.

## The @mark token is the signal

A note opening `@mark` reaches Mark's Asana inbox. A note without it is posted and recorded,
but stays silent. That is the whole signalling mechanism.

### What it actually does, and what it does not

`sync.py` sends the documented rich-text mention — `html_text` carrying
`<a data-asana-gid="…"/>`. On its own it reaches the thread and nothing else: Asana does not
auto-add the person as a collaborator for an API comment the way it does for one typed in the
web UI.

So `leave_progress_comment` first calls `POST /tasks/{gid}/addFollowers` for `ASANA_USER_GID`,
**waits `MENTION_FOLLOW_WAIT` (35) seconds**, then posts. The note then arrives as a real
mention: in the inbox filtered to **Mentioned**, in the normal inbox, and as a browser
notification. If Mark already follows the task there is nothing to add and no wait.

**The wait has to be 30 seconds or more.** Asana does not count a comment as a mention if it
is posted less than 30 seconds after the user was made a collaborator. Asana's staff confirmed
this as a bug on the Asana forum on 2026-11-17 and gave the 30-second wait as the workaround.

| Posted via | "Mentioned" filter | Normal inbox | Browser |
|---|---|---|---|
| `sync.py` with `@mark` | **yes** | yes | yes |
| `sync.py` without it | no | no | no |

History, so nobody repeats it: from 2026-11-05 the wait was 3 seconds, and six tests on
2026-11-06 (with and without the pre-add, three markup variants) all missed the filter, which
was read as "the API cannot mention". The probe on SLT-013 on 2026-11-17, at 37 seconds,
reached it. Recorded in BSTD-878.

**Do not remove the collaborator add, and do not shorten `MENTION_FOLLOW_WAIT` below 30
seconds** until Asana fixes the bug. Without the add the note arrives nowhere; with a shorter
wait it arrives, but not under Mentioned.

**Do not try to fix the markup.** It is the documented form and was never the problem.

The cost is up to 35 seconds per fresh `@mark` note on a task Mark does not yet follow, paid
once per task.

### Slack carries the signal instead

A fresh `@mark` post also pings Slack, via `_ping_slack` in `sync.py`. Three rules:

- **The comment is posted first** and its GID returned regardless. A Slack
  outage never costs the note.
- **Fresh posts only.** An edited note does not re-notify in Asana either, and
  pinging on every re-sync would flood the channel it exists to keep usable.
- **It never raises.** `notifier.notify()` returns `False` rather than throwing,
  the import is guarded, and a failure logs a warning naming the task — so a
  lost signal leaves a trace instead of vanishing, which is what made the
  original diagnosis possible at all.

The message carries the local ID and task name as its subject, the note's first
block and a task URL as the body, and the remaining blocks as details. It goes
to `SLACK_WEBHOOK_URL`; a dedicated `review` channel would be one entry in
`notifier.CHANNEL_WEBHOOKS`.

Clicking the link opens the task in the Asana Chrome instance rather than the
main browser, via `~/bin/url-dispatch.sh` registered as the system https
handler. Without it a Slack link lands in a browser that is not signed in.

The 2026-11-05 work (found on BD-204) was right that `@mark` notes had been invisible and right
about the fix.

Only a **fresh post** can notify. Re-mentioning someone on an edited story raises nothing, so
a comment that already missed the inbox cannot be rescued by editing it. **Posting it again
does work** — `leave_progress_comment` does no text-based dedupe, so without a story GID it
adds the follower and posts a new story, identical text and all, which notifies. That leaves
two identical comments on the thread: worth it for a comment Mark never saw, not for anything
he has already replied to. Read the thread before reposting from a list.

This is why `sync.py` must never add the token unconditionally. Use the token for **review** and **blocked** notes — the two cases where
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

## The two write paths

Both go through `sync.py` — never the Asana API directly (ADR 002: all mutations use the
bainbot PAT).

| Path | Used by | How |
|---|---|---|
| A task's `**Progress:**` line in `asana-mirror.md` | Any project session; the scheduled sync posts it | One mirror line, `\|\|`-separated |
| `sync.py --comment --task-gid {GID} --comment-text "…"` | `blocked-sweep`, one-off posts | Same renderer, same template |

`--comment` used to post raw text, so a `@mark` token in it was literal: no collaborator was
added and the note never reached Mark. It now runs through `leave_progress_comment` like any
Progress note.

**`--comment` cannot correct a note by itself.** A bare task GID carries no project state, so
it cannot find the story it posted last time and posts afresh — leaving the old note above the
new one, the note-plus-contradiction this page forbids. A correction needs the story GID,
which the posting run prints:

```bash
python3 studio/sync.py --comment --task-gid {GID} --story-gid {STORY_GID} \
  --comment-text "{the corrected note}"
```

From a project mirror there is nothing to pass: the scheduled sync tracks the story GID in
`asana-ids.json` and edits in place on its own.

One edge: `--comment` writes no mirror and no state, so the follower it adds normally survives
(the story bumps `modified_at`, so the next run pulls). If a scheduled sync stamped that same
task in the same window, the next run reads the mirror as newer and removes the follower once.
The note still arrived; only a later mention on that task would be silent. Posting the next
note re-adds the follower, so nothing needs doing.

## Enforcement

`validate_progress_note` runs before anything is posted, on **both** write paths. A note over
a limit is **not posted at all** — an error naming the task goes to `studio/sync.log`, the
note stays in the mirror to be rewritten, and the task's own state (section, assignee, fields)
still syncs, so the work still appears in Mark's task list. `--comment` exits 1.

| Limit | Value | Catches |
|---|---|---|
| Summary | 500 chars | The narrative dump |
| Any one block | 150 chars | A paragraph where a line belongs |
| Block count | 6 | More than 3 `Check:` items |
| Location in an `@mark` summary | none | A path, branch, commit or URL outside `Where:` |
| `Where:` comment | 300 chars | Detail dressed up as a location |
| `Done` with open subtasks | needs `Subtasks:` | Completion recommended over unfinished steps |

Tightened 2026-11-17 at Mark's request: the 900/200/8 limits let wordy notes through. A note under every
limit passes whatever its shape, so skills with their own short formats keep working. A
`Checked {date}.` heartbeat is exempt.

Posting a wall of text with a warning was considered and rejected: it puts Mark back where he
started, which is the whole problem.

## Not built

- **Screenshot attachments.** `sync.py` downloads attachments (`fetch_task_attachments`) but
  cannot upload. Asana takes a multipart `POST /attachments`; a visual check ("the header at
  720px") would read better as one image than as sixty words. Deferred, not rejected. If it
  is built, it needs a two-image ceiling and must skip re-downloading bainbot's own uploads,
  since `.png` is in `ATTACHMENT_EXTS`.
- **Silent auto-close for low-risk fixes.** Considered and dropped: everything goes to review
  for now. The mention filter already keeps routine notes off Mark's radar without Claude
  having to judge its own risk.
- **The other three skills with their own note formats** — `studio-delivery-gate`, `feature`,
  `end-session` — inherit the plumbing (mention support, edit-in-place) but still write
  free-form notes, because "finished a build, needs review" is not their shape. They post
  without the token, so they stay silent until given it.

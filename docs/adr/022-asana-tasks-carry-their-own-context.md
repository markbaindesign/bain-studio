# ADR 022 — Asana tasks carry their own context; subtasks are for steps only

Date: 2026-10-15
Status: Accepted (2026-10-15)
Related: [new-task](../utilities/new-task.md), [new-subtask](../utilities/new-subtask.md)

## Context

Subtasks in Asana are much less visible than top-level tasks. The assignee sees a subtask in
their own My Tasks list, but other people on the team don't see it in the project. That makes
subtasks hard to follow from a team view and hard to schedule.

There is also a temptation to let a task's place in a hierarchy explain what it is about. For
example, site feedback gets split as *Feedback > site section > page or issue*. The leaf task
then reads as "Header spacing", and you have to look at its parents to know which section it
belongs to. If the task is moved, promoted, or multi-homed (into Studio Looper, say), that
context is lost.

## Decision

1. **Don't use subtasks for anything significant.** A subtask is for the assignee to set out
   the steps of one task that can easily be done in a single sitting. Anything bigger is a
   top-level task.
2. **Promote a subtask once it outgrows that.** Asana lets you turn a subtask into a top-level
   task. Do that as soon as it needs its own timeframe, assignee, or discussion.
3. **Feedback items are never subtasks.** Each one has its own timeframe and rhythm, so each one
   is a top-level task.
4. **Every task stands on its own.** The title and description carry all the context needed to
   understand the task: site section, page, client. Don't rely on the parent task, section, or
   position in a list to supply it. Write "About page - header spacing", not "Header spacing"
   under an "About page" parent.
5. **Group related tasks with tags or custom fields, not hierarchy.** A recurring label (a site
   section, a feedback round, a theme of work) goes on as a tag, which works across projects
   and the workspace. If it's a fixed set of values used within one project, such as site
   sections, a custom field works too. Both stay on the task wherever it moves, including
   when it's a subtask.

## Consequences

- `sync.py --create-subtask` is still useful for breaking a task into steps. It's the wrong tool
  for splitting up work that others need to see or schedule. Subtasks don't appear in the
  local mirror either, which is another reason not to let real work live there.
- Task titles get a little longer because they repeat context a hierarchy would have implied.
  That's intended.
- Agents creating tasks (studio-pm, looper, `/issue`, `/qa-capture`) should follow the same
  rules: top-level tasks with self-contained titles, and tags or fields for grouping.

## Addendum 2026-11-19: no client name in task titles

Rule 4 no longer puts the client in the title. Every task's home project already names the
client, and Asana shows the project on the task wherever it is multi-homed, so a client prefix
only repeats it. Write "Turn off debug logging", not "Acme Ltd: turn off debug logging". The
title still names the page or site section. The description can name the client where that
helps.

## Addendum 2026-11-25: no prefix of any kind in task titles

Mark's call. A title is the task itself, written as a plain sentence: no `Label:` in front of
it, whether the label is a client, a tool (`sync.py:`), a component (`Looper runner:`), a
workstream (`Theme review:`, `KF archive:`) or anything else. Write "Give tasks that arrive
with a Local ID already in use a fresh one", not "sync.py: give a fresh Local ID to tasks…".
The same goes for the project's own name (`Theme review:` on a task in the Theme Review
project) and for a kind (`Question:`, `Decision:`). A prefix makes a narrow list unscannable,
since every row starts with the same words. Where the page, section or tool is needed to
understand the task, it goes inside the sentence ("Stop the looper runner starting empty
sessions"). Grouping uses Asana's own links: project, section, tag, custom field,
dependency or parent. Mark never prefixes the tasks he writes; agents match them.

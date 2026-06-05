---
name: nurture
description: Spec nursery manager. No args = triage pass over all drafts (pursue/defer/discard). Named arg = full grill-me interview to flesh out a specific stub into a complete spec.
---

## Mode A — Triage (no args)

List every file in `context/specs/drafts/`. For each one:
1. Read the file
2. Print a one-line summary: `[filename] — {title} ({source tag if present})`
3. Ask the user: **pursue**, **defer**, or **discard**?

After each decision:
- **pursue** — add a `status: pursue` line to the stub's frontmatter (or top of file if no frontmatter) and move on
- **defer** — add `status: defer` and move on
- **discard** — confirm once, then delete the file

After all stubs are triaged, print a summary:
```
Triage complete — {N} pursue, {N} defer, {N} discarded
Pursue list: {names}
Run `/nurture {name}` to flesh out any of these.
```

## Mode B — Flesh out a stub (arg = spec name fragment)

Find the matching file in `context/specs/drafts/` by name fragment. Read it fully.

Then run a focused grill-me interview to build it into a complete spec. Follow the grill-me rules:
- One question at a time
- Walk every branch of the decision tree
- Provide a recommended answer for each question
- If a question can be answered by exploring the codebase, do that instead of asking

Branches to cover (skip any already answered in the stub):
1. **Problem** — what pain does this solve, for whom, how often?
2. **Sources & inputs** — what data/systems does it touch?
3. **Output** — what does done look like? Files, UI, API, side effects?
4. **Stack** — language, libraries, auth strategy
5. **Phases** — what's Phase 1 (smallest useful thing)?
6. **Risk** — what's the hardest part?
7. **Prerequisites** — any one-time setup needed?

When the interview is complete, rewrite the stub file as a full spec using the gestor-collector spec at `context/specs/gestor-collector.md` as a format reference.

Ask the user: "Move to candidates for `/review-spec`?"
- Yes → move file from `context/specs/drafts/` to `context/specs/candidates/`
- No → leave in drafts

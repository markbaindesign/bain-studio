---
name: brand-voice
description: >
  Tune Mark's brand voice rules — what he would and wouldn't say in a particular
  context (cold outreach, client messages, social posts, proposals, etc). Reads and
  updates the master brand voice doc at
  /media/data/Dropbox/Work/Content/Brand Voice/brand-voice.md. Accessible from any
  project. Trigger phrases: "brand voice", "tune my voice", "voice rules",
  "/brand-voice".
allowed-tools: [Read, Write, Edit, Bash]
---

# Brand Voice Tuner

Maintains one file: `/media/data/Dropbox/Work/Content/Brand Voice/brand-voice.md` —
the canonical source for Mark's voice, broken into a universal **Core voice** and a
set of **Contexts** (situational registers: what changes, what stays fixed).

This is Mark's personal/general voice reference — broader than the studio-only
agent-facing summary in `context/internal/brand.md` (which now just points here).

---

## Step 1 — Determine mode

- **No argument**: show the list of contexts already documented (section headers
  under `## Contexts`) and ask which one to tune, or whether to run `audit`.
- **"show" / "list"**: read and print the full master doc, then stop.
- **"audit"**: go to Step 5 (consistency check across contexts).
- **Anything else** (a context name or description, e.g. "cold outreach emails",
  "LinkedIn comments", "invoice chase-up emails"): go to Step 2.

If the master doc doesn't exist yet, create it first (Step 1a) before continuing.

### Step 1a — First-run bootstrap

If `/media/data/Dropbox/Work/Content/Brand Voice/brand-voice.md` doesn't exist,
create it with:
- A `## Core voice` section seeded from `context/internal/brand.md`'s existing
  Do/Don't lists (the rules that apply everywhere, regardless of context)
- An empty `## Contexts` section with one pre-populated example ported from
  `context/internal/brand.md`'s "Client messages" section, since that's already a
  real context-specific register Mark defined
- A short header explaining the file's purpose (canonical voice source, contexts
  layer situational exceptions on top of Core voice, agent-facing consumers should
  read `context/internal/brand.md` for the compact pointer version)

Tell Mark this bootstrap happened before proceeding to the interview.

---

## Step 2 — Context interview

One context at a time. Ask conversationally, not as a rigid form — but make sure
you come away with enough to write a real Do/Don't section. Useful prompts:

1. "Give me an example of something you'd actually say in this context."
2. "Now something you'd never say here, even though it might work in another
   context."
3. "How does this differ from your default voice — more formal, more casual,
   shorter, warmer, blunter?"
4. "Any fixed conventions — greetings, sign-offs, emoji, exclamation points,
   specific words you always/never use here?"
5. "Got a real example — an actual message, email, or post — you can paste in?"
   Real examples beat invented ones; use them verbatim as the Do/Don't illustrations
   where possible.

Stop asking once you have: a one-line tone descriptor, at least 2-3 concrete Do
bullets, at least 2-3 concrete Don't bullets, and ideally one real example.

Don't invent rules Mark hasn't stated or confirmed — same discipline as the
`/skills` registry: only what he's actually told you goes in the file.

---

## Step 3 — Write the context section

Format, matching the existing "Client messages" style in `context/internal/brand.md`:

```markdown
### {Context name}

{One-line scope note — when this register applies, and what it's NOT for.}

- {Do/Don't rule, specific and imperative}
- {...}
```

Mix Do and Don't rules in one flat list (that's the existing convention — see
"Client messages") rather than separate Do/Don't subheadings, unless the context
has enough rules to need the split (that's fine for Core voice, which already does
this).

If a real example was given, include it as a short blockquote under the rules.

Add the new section under `## Contexts` in the master doc. If the context already
exists, update it in place rather than duplicating — ask Mark to confirm whether
this is a revision or a genuinely new context if the name is ambiguous.

---

## Step 4 — Confirm

Read back the section you wrote in full and ask Mark to confirm it's accurate
before considering it final. Small wording tweaks are fine to apply directly from
his reply.

---

## Step 5 — Audit (on demand)

Read the full master doc. Check for:
- Contexts that contradict Core voice without flagging it as an intentional
  exception (e.g. Core voice says no exclamation points, a context uses them
  freely with no note explaining why)
- Contexts that contradict each other
- Contexts with only vague/generic rules that don't actually constrain anything
  (candidates for a follow-up interview)

Report findings plainly; don't auto-fix contradictions — ask Mark which side wins.

---

## Rules

- Never add a rule Mark hasn't stated in this conversation — no inferring from
  "similar" contexts.
- Core voice changes are rare and higher-stakes than context additions — if asked
  to change Core voice, read back the specific line being changed and confirm
  before writing.
- Keep `context/internal/brand.md`'s voice section as a short pointer only — don't
  let it drift back into a full duplicate of this file.
- This file is personal/general (all of Mark's writing, not just studio agent
  output) — a context doesn't have to be studio-related to belong here.

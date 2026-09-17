---
name: onboard-client
description: Orchestrates onboarding a new WordPress client — quizzes Mark for project details, then chains commission, DDEV codebase setup, tech access request, and Dropbox folder creation. Prints a manual-steps checklist for anything that can't be automated (Harvest client/project, Chrome bookmarks, git remote). Invoke when a new WordPress client deal has been signed and it's time to set up the project.
argument-hint: <client name>
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion]
---

# Onboard Client

Turns a signed WordPress deal into a fully set-up studio project. Orchestrates
existing skills in sequence; where no automation exists yet (Harvest,
Chrome bookmarks, remote git repo), it stops and tells Mark exactly what to
do by hand rather than guessing or attempting something fragile.

**The sequence:** Quiz → Commission (Asana + registry) → Tech access request
→ DDEV codebase → Dropbox folder → Manual-steps checklist.

Tech access goes out early, right after commissioning — the default project
type ("existing site") can't be pulled into DDEV until the client responds
with credentials, so there's no point blocking the rest of the workflow on
it. If this ordering is wrong for a given project, say so and skip ahead.

---

## Step 1 — Quiz

Ask Mark for (don't guess):

- **Client name** — for the Dropbox folder, Asana project, and tech access
  greeting. Use `$ARGUMENTS` if given, otherwise ask.
- **Contact name** — who the tech access request is addressed to (may differ
  from the client/company name).
- **Project name** — short descriptive name for Asana/CLAUDE.md (e.g. "Andrew
  Techstyle Rebuild").
- **Prefix** — 2–5 uppercase chars for Asana task IDs (e.g. `TSTY`). Suggest
  one from the client name if not given.
- **Project type** — this branches Steps 3–4:
  - **Existing site** (default, most common) — Mark inherits a live WordPress
    site. DDEV gets set up as an empty shell; pulling the actual site content
    is a manual step once tech access arrives (Step 3 covers this).
  - **Fresh install** — brand new build, no existing site. DDEV gets a clean
    WordPress core install immediately, no waiting on client credentials.
- **Domain** (if known) — used for the DDEV local URL and later DNS/staging
  work (out of scope here — that's `/periphetes`).

Confirm all of these back before proceeding:

```
Ready to onboard:
  Client:   {client}
  Contact:  {contact}
  Project:  {project name}
  Prefix:   {PREFIX}
  Type:     {existing site | fresh install}
  Domain:   {domain or "unknown"}

Proceed? (y/n)
```

---

## Step 2 — Commission

Codebase path: `/media/data/dev/ddev/{slug}` (slug = lowercase, hyphenated
client/project name — this matches the existing convention, e.g. the empty
`techstyle` scaffold already there).

Run `/commission` with the details from Step 1. `/commission` normally looks
for a spec file first — for client onboarding there usually isn't one, so
skip that lookup and hand it the four fields directly (name, prefix, path,
description) when it asks. This gives you:

- `/media/data/dev/ddev/{slug}` created + git-initialised (local only — see
  the manual-steps note on remote repos)
- Asana project created, project GID captured. `sync.py` automatically uses
  `ASANA_USER_PAT` from `bain-studio/studio/.env` when present, so this is
  owned by Mark, not bainbot — that's already the case today. Renaming a
  project and changing its icon/color in Asana are owner-only actions, so if
  that token is ever removed and projects fall back to bainbot ownership,
  this is the thing that breaks — check `sync.py`'s own output for "Using
  Mark's API token" vs. the "ASANA_USER_PAT not set" warning, and flag it to
  Mark if it's the latter.
- `CLAUDE.md` written with the `## Asana` block
- Project registered via `/register-project` (projects.json, docs/projects/,
  studio CLAUDE.md table)

---

## Step 3 — Tech access request

Invoke `/tech-access-request` with the contact name from Step 1 and the Asana
project GID captured in Step 2 (`--project-gid`). Ask Mark which items (if any)
he already has for this client, same as that skill normally does.

That skill produces three things, not one: the client-facing request
(`.md` + `.pdf`), **one Asana task per access item** plus a "Tech access
complete" sign-off task, and `access-record.md` — the internal record of what
access actually exists, filled in as items land. Pass the GID or the tasks
land nowhere, and Asana is where Mark monitors this.

Do not duplicate those access tasks in the Step 6 checklist. They already
exist on the board by the time Step 6 runs.

Save the output into the client's Dropbox folder, not the codebase and not the
shared template folder:
`/media/data/Dropbox/Work/Projects/Client/{Client Name}/Dev Ops/tech-access-request.md`
and `.pdf`.

It goes under `Dev Ops/` because that is where the hosting, DNS and access
notes it produces already live. It stays out of the repo because it is a
client-facing document, not code — the repo's `CLAUDE.md` points at it rather
than holding a copy, so there is only ever one version.

This step runs before Step 5 creates the folder structure, so create the
directory first (`mkdir -p`) rather than assuming it exists. Step 5 fills in
the rest of the tree around it.

If **project type = existing site**: note explicitly that DDEV in Step 4 will
be an empty shell until this request is answered. Add "pull existing site
into DDEV" to the manual-steps checklist in Step 6 with the exact commands to
run once credentials land (see Step 4).

---

## Step 4 — DDEV codebase

Inside `/media/data/dev/ddev/{slug}` (created in Step 2).

**WordPress always lives in `public_html/`, never at the repo root.** This is
the studio standard, set by the VVV-era projects (`nore`, `buddhist-film-
foundation`) and carried forward to DDEV. A project with `wp-admin/` sitting
next to `CLAUDE.md` is wrong and has to be restructured later, so get it right
on the first pass.

The full directory standard:

```
{slug}/
├── public_html/     ← WordPress core + wp-content. The docroot.
├── scripts/         ← deploy.sh, sync helpers, one-off migration scripts
├── import/          ← DB dumps coming IN (from the client's host)
├── export/          ← artefacts going OUT
├── backups/         ← local safety copies before destructive work
├── docs/            ← project docs, ADRs
├── qa/              ← QA inbox, per the /qa skill
├── .ddev/config.yaml
├── wp-cli.yml
├── .gitignore
└── README.md
```

`provision/` and `log/` are deliberately absent — they are VVV artefacts
(`vvv-init.sh`, nginx logs) and DDEV covers both.

**Do not build this by hand.** One call to `/scaffold-dir` produces the whole
tree above, the three-tier `.gitignore`, `wp-cli.yml` with `path: public_html`,
the DDEV config with **`docroot: public_html`**, and a git repo on `main` with
`develop` branched:

```bash
/scaffold-dir /media/data/dev/ddev/{slug} {slug} --wordpress --ddev \
    --php 8.2 --db mariadb:11.8 --wp-version latest \
    --plugin {slug}-custom --theme {slug}-theme
```

Match the client's host on `--php`, `--db` and `--wp-version` — a legacy site on
PHP 7.4 and MySQL 5.7 must be scaffolded that way, or local will not match live.

Then:

1. `ddev start`
2. For a **new build**: `./scripts/install-wp.sh` — installs WordPress with admin
   user `bain_324` and prints a generated password. Akismet and Hello Dolly are
   removed; one default theme is kept so the site renders.
   For a **migration**: import the client's files and database instead, and skip
   the install script.

Two things `/scaffold-dir` does **not** do, which still need doing by hand:

- The database name does not follow Periphetes' convention (`bd324_` prefix) —
  DDEV names it `db`. Set it in `.ddev/config.yaml` if the project needs it.
- `CLAUDE.md` and `.claude/settings.json` come from `/commission` and
  `/register-project`, not from the scaffolder.

See ADR 016 for why this is `/scaffold-dir` rather than a separate `wp-scaffold`
tool, which was considered and rejected.

Then branch on project type from Step 1:

- **Fresh install**: run `ddev wp core download` and `ddev wp core install`
  with placeholder admin credentials (Mark's own, not the client's — the
  client's WP account request goes out via the tech access doc, not here).
  Then run `/wp-defaults` in the same directory — it sets the standard debug
  wp-config constants and clears WordPress's default sample content/plugins
  (Hello Dolly, Akismet, Jetpack if present, the sample post/page). This
  step is fully automated, nothing further needed from Mark.

- **Existing site**: leave DDEV configured but empty. Do **not** attempt to
  pull site files or a database — there's nothing to pull yet. Add to the
  Step 6 checklist:
  ```
  Once tech access arrives:
    - Pull files: rsync/SFTP the client's docroot into
      /media/data/dev/ddev/{slug}/public_html/
      (NOT the repo root — that produces the wrong structure)
    - Pull DB: dump into import/, then `ddev import-db --file=import/...`
    - `ddev wp search-replace 'https://livesite.com' 'https://{slug}.ddev.site'`
  ```
  This is a "come back once you have access" item, not something this skill
  can finish today.

---

## Step 5 — Dropbox folder

Create at `/media/data/Dropbox/Work/Projects/Client/{Client Name}/` with:

```
Admin/
.claude/
CLAUDE.md
Content/
Design/
Dev/
Dev Ops/
Docs/
```

(No `Showcase/` — dropped from the older template intentionally.)

`Dev Ops/` will already exist and hold the tech access request from Step 3 —
create the rest around it, don't overwrite it.

Populate:

- `CLAUDE.md` — same `## Asana` block written in Step 2 (GID, prefix, project
  name), so this Dropbox folder and the DDEV codebase folder both resolve to
  the same Asana project.
- `.claude/settings.json` — run `/default-perms` from inside this folder.

Note: this Dropbox folder is separate from the codebase at
`/media/data/dev/ddev/{slug}` — the codebase stays out of Dropbox
deliberately (git + Dropbox sync don't mix well). `Dev/` and `Dev Ops/` here
are for client-supplied assets, exports, and ops artefacts, not the working
tree.

---

## Step 6 — Manual-steps checklist

Print a final checklist, and — since the Asana project now exists from Step
2 — also create one task per item in it, so the checklist lives where the
rest of the project's work already lives, not just in this chat transcript.

Use `/seed-tasks {gid} "Task 1" "Task 2" ...` with one task per item below
(skip the existing-site item if this was a fresh install):

```
Manual steps remaining for {Client}:

[ ] Harvest — create client "{client}" and project "{project name}" in the
    Harvest UI (no write API wired up yet — see harvest_client.py, read-only
    today). Suggested rate: {ask or leave blank}.

[ ] Chrome bookmarks — add a folder for {Client} with:
    - Asana project: {asana project url}
    - DDEV local: https://{slug}.ddev.site
    - Dropbox folder: {dropbox path}
    (No tooling for this yet — Chrome's bookmarks file is only safely
    editable while Chrome is closed, so this stays manual for now.)

[ ] Git remote — deferred. When ready, run /repo-create from
    /media/data/dev/ddev/{slug}.

[ ] (existing-site projects only) Pull the live site into DDEV once tech
    access comes back — see Step 4 for the exact commands.
```

Suggested task names for `/seed-tasks`:
- "Create Harvest client + project for {Client}"
- "Add Chrome bookmarks folder for {Client}"
- "Create git remote for {slug} (optional/deferred)"
- "Pull {Client}'s live site into DDEV once tech access arrives" (existing-site only)

Report which tasks were created (with links) alongside the printed checklist
— the checklist stays useful as a plain-text summary even though the tasks
are now the actual source of truth for follow-up.

---

## Guard rails

- **Don't guess project type, prefix, or client name** — always ask in
  Step 1.
- **Never install WordPress at the repo root.** Docroot is `public_html/`,
  always. `ebiz-global` and `techstyle` predate this rule and are both wrong;
  don't copy their layout when looking for a reference. Use `nore` or
  `buddhist-film-foundation` instead.
- **Don't let the tech access step run without a project GID** — the Asana
  tasks are how Mark tracks access, and a run that skips them looks finished
  while leaving nothing to monitor.
- **Watch commission's output for the ownership warning** — `sync.py` uses
  `ASANA_USER_PAT` (`bain-studio/studio/.env`) automatically when present, so
  projects are owned by Mark today. If that ever changes, name/icon become
  owner-only fields bainbot can't fix — flag it immediately rather than
  letting the rest of the chain run on top of a bainbot-owned project.
- **Don't attempt Harvest writes or Chrome bookmark edits** — no safe
  automation exists for either; always defer to the manual checklist.
- **One client at a time.**

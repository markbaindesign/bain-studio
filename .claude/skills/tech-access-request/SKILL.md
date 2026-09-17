---
name: tech-access-request
description: Generate a personalised Tech Access Request doc for a client — greets them by name and lets pre-obtained items be checked off. Produces a branded PDF via brand-doc, one Asana task per access item, and an access record to fill in as they land. Trigger phrases " tech access request", "access request doc", "/tech-access-request".
argument-hint: <contact name> [--project-gid GID]
allowed-tools: [Bash, Read, Write]
---

# tech-access-request

Personalises the master Tech Access Request template for a specific client,
renders it as a Bain Design branded PDF, raises one Asana task per access item,
and opens the access record those tasks fill in.

Three artefacts come out of one run:

| Artefact | Where | What it is |
|----------|-------|------------|
| `tech-access-request.md` / `.pdf` | client's `Dev Ops/` | what was **asked for** — client-facing |
| Asana tasks | the project's Asana board | how progress is **tracked** |
| `access-record.md` | client's `Dev Ops/` | what was **received and verified** — internal |

Mark monitors this work in Asana, so the tasks are not optional garnish — a run
that produces the PDF but no tasks has not finished.

## Master templates

`/media/data/Dropbox/Work/Content/Tech Access Request/tech-access-request-template.md`
`/media/data/Dropbox/Work/Content/Tech Access Request/access-record-template.md`

This file is the single source of truth for the request copy. It contains a
`{{CLIENT_NAME}}` placeholder in the greeting and a GFM task list (`- [ ]`) for
every access item that can be requested:

1. WordPress Access
2. Server Access
   - (S)FTP Access
   - Shell (SSH) Access
   - Database Access
   - cPanel or Hosting Control Panel Access
3. Repository Access

If the user asks to update the wording of the request itself, edit this file
directly rather than the generated output — it's the shared template every
future run reads from.

## Steps

1. **Get the client name.** Ask if not given ("Dear ___,").

2. **Find out what's already in hand.** Ask the user which of the items above
   Mark already has access to (e.g. from a previous engagement, a shared
   staging environment, or an existing repo collaborator invite). Anything
   already available should be pre-checked so the client isn't asked for it
   again — leave everything else unchecked. Don't assume; ask explicitly. A
   quick way to ask: "Which of these do you already have for this client?
   WordPress admin / SFTP / SSH / Database / cPanel / Repo access — or none?"

3. **Determine the output location.** Default to the client's Dropbox folder:
   `/media/data/Dropbox/Work/Projects/Client/{Client}/Dev Ops/tech-access-request.md`
   (and the matching `.pdf`). `Dev Ops/` is where the hosting, DNS and access
   notes this request produces already live.

   This is a client-facing document, so it does **not** go in the codebase —
   a project repo should point at the Dropbox path from its `CLAUDE.md`, never
   hold its own copy, or the two drift.

   Create the directory with `mkdir -p` if it doesn't exist yet. If the client
   has no Dropbox project folder and it isn't obvious which client this is for,
   ask where to save it rather than guessing.

4. **Build the personalised Markdown.** Read the master template, then:
   - Replace `{{CLIENT_NAME}}` with the client's name.
   - For each pre-obtained item's checkbox line, change `- [ ]` to `- [x]`.
   - Leave everything else unchanged.
   - Write the result to the output path from step 3.

5. **Render the PDF.** The `brand-doc` tool doesn't understand GFM task-list
   checkboxes — it will render `[ ]`/`[x]` as literal text. Before calling it,
   write a temporary copy where checkbox markers are swapped for glyphs:
   - `- [x]` → `- ☑`
   - `- [ ]` → `- ☐`
   - `💡 ` → `**Note:** ` — the emoji has no glyph in brand-doc's fonts and
     renders as a tofu box on the client's copy.

   **Name the temp file for the document, not the transform.** `brand-doc`
   takes the PDF's cover title from the input filename, so a temp called
   `glyphs.md` ships a client-facing PDF titled "Glyphs". Name it
   `Tech Access Request - {Client}.md`.

   Then run:

   ```bash
   brand-doc "/tmp/.../Tech Access Request - {Client}.md" "/path/to/Tech Access Request - {Client}.pdf"
   ```

   Check the rendered cover page before sending.

   Delete the temporary glyph file afterwards — the checkbox-syntax `.md` from
   step 4 is the one that stays on disk (it's the readable/editable record).

6. **Create the Asana tasks.** One task per access item, so each is tracked
   where Mark actually monitors work. Skip any item pre-checked in step 2 —
   it's already in hand and does not need chasing.

   Find the project GID from the project's own `CLAUDE.md` (`ASANA_PROJECT_GID`)
   if `--project-gid` wasn't passed. If neither is available, say so and skip
   this step rather than creating tasks on the wrong board.

   ```
   /seed-tasks {gid} \
     "Tech access: WordPress admin account (bain_324)" \
     "Tech access: (S)FTP credentials" \
     "Tech access: Shell (SSH) access" \
     "Tech access: Database access" \
     "Tech access: Hosting control panel access" \
     "Tech access: Git repository access" \
     "Tech access complete — verify and sign off access record"
   ```

   The final task is the gate, not a formality. It closes only when every row
   of the access record reads Verified or N/A and the sign-off block is filled
   in. Note in the report that closing it early defeats the point of the record.

   `/seed-tasks` uses the bainbot PAT. Never write to Asana via the MCP.

7. **Open the access record.** Copy `access-record-template.md` to
   `{Dev Ops}/access-record.md`, replacing `{{CLIENT_NAME}}`,
   `{{PROJECT_NAME}}` and `{{DATE}}` (ISO, `YYYY-MM-DD`).

   Set the status of each row in section 2 to match what step 2 established —
   `Requested` for items in the outgoing request, `Received` for items Mark
   already had. Nothing starts as `Verified`; that is earned by logging in.

   This file stays Markdown only. It is an internal working document that gets
   edited repeatedly as items land, so it does **not** get a branded PDF —
   `brand-doc` output is for things clients read.

8. **Report back** the paths to the saved `.md` and `.pdf`, the access record
   path, and the Asana tasks created (with links). Offer to open the PDF
   (`xdg-open`).

## Filling the record in

As each access item comes back, update its row in `access-record.md` and close
the matching Asana task. The two move together — a closed task with a blank row
means the record has stopped being true, and the record is the thing anyone
reads six months later when the client asks who has access to what.

Sections 3 to 6 (server capabilities, backups, DNS, WordPress) are answered by
**testing**, not by asking. Once SSH or panel access lands, go and check whether
WP-CLI is really there, whether cron is real, when a backup was last restored.
The host's sales page is not evidence.

When everything is Verified, populate the project's `dev-ops.md` from the record
and close the sign-off task.

## Notes

- See the `brand-doc` skill for details on the underlying PDF tool.
- Keep client-identifying content (name, any credentials) out of the shared
  master template — personalisation always happens in the per-client copy,
  never by editing the template in place.

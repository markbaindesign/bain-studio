---
name: tech-access-request
description: Generate a personalised Tech Access Request doc for a client — greets them by name and lets pre-obtained items be checked off. Produces a branded PDF via brand-doc. Trigger phrases " tech access request", "access request doc", "/tech-access-request".
allowed-tools: [Bash, Read, Write]
---

# tech-access-request

Personalises the master Tech Access Request template for a specific client and
renders it as a Bain Design branded PDF.

## Master template

`/media/data/Dropbox/Work/Content/Tech Access Request/tech-access-request-template.md`

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

3. **Determine the output location.** Default to a `Tech Access Request -
   {Client}.md` file in the current project directory (the project the user
   is working in when they invoke this skill). If there's no obvious project
   context, ask where to save it.

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

   Then run:

   ```bash
   brand-doc /path/to/temp-with-glyphs.md "/path/to/Tech Access Request - {Client}.pdf"
   ```

   Delete the temporary glyph file afterwards — the checkbox-syntax `.md` from
   step 4 is the one that stays on disk (it's the readable/editable record).

6. **Report back** the paths to the saved `.md` and `.pdf`, and offer to open
   the PDF (`xdg-open`).

## Notes

- See the `brand-doc` skill for details on the underlying PDF tool.
- Keep client-identifying content (name, any credentials) out of the shared
  master template — personalisation always happens in the per-client copy,
  never by editing the template in place.

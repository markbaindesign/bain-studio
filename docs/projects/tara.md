---
tags:
- studio-project
prefix: TARA
name: KF Tara Mini-Site
status: active
client: Khyentse Foundation
type: client
repo: git@bitbucket.org:markbaindesign/kf-tara-web.git
sector: Non-profit · Religion · Culture
stack: Astro · astro:i18n · static output, no CMS/backend
path: /media/data/dev/misc/kf-tara-web
asana: "yes"
asana_project_gid: "1216767786076596"
asana_project_url: "https://app.asana.com/1/512209774840/project/1216767786076596/list/1216778171299390"
qa: "no"
inbox: "no"
open_tasks: 0
current_focus: ""
next_action: ""
---

# KF Tara Mini-Site (TARA)

Client project. Standalone Astro mini-site for Khyentse Foundation's Tara
Altar content (practice resources, sadhanas, chants, gallery, teachings).
Independent of the main KF site rebuild (`KF-WEB`) — own visual identity,
own codebase. Billed hourly against KF's existing retainer, not a
fixed-price deliverable.

## Key contacts

- **Khyentse Foundation** — client
- Maryann Lipaj (KF Creative Director) — owns visual design, not yet
  delivered as of registration

## Asana

Existing Asana project "Tara Website" (not created via `sync.py --create`
template flow) — GID `1216767786076596`. Run
`python3 studio/sync.py --setup --project TARA` to wire up the Local ID /
Last Synced custom fields, and confirm bainbot has been added as a member
of the project before running `sync.py` against it.

## Notes

- Full spec and scoping notes live in Dropbox: `Khyentse Foundation/Tara
  Mini-Site/Docs/` — see project `CLAUDE.md` for exact filenames.
- Content source is the live site (`khyentsefoundation.org/tara-altar/`),
  not yet exported/migrated.

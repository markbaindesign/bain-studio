---
tags:
- studio-project
prefix: AW
name: Alex Wright Site
status: active
client: Alex Wright
type: client
repo: git@ssh.bitbucket.org:markbaindesign/alex-wright.git
sector: Personal brand · Speaker / Author
stack: WordPress FSE block theme · ACF Pro · VVV
path: /media/data/dev/vvv/clients/www/alex-wright
asana: "yes"
qa: "no"
client_docs: "/media/data/Dropbox/Work/Projects/Client/Alex Wright"
inbox: "no"
open_tasks: 16
current_focus: Footer restore (awaiting Alex), plugin/PHP follow-ups, backup rework
next_action: "AW-012/014 - deploy restored footer once Alex approves"
---

# Alex Wright Site (AW)

Client project. Alex Wright's personal site (alexwright.com) - WordPress FSE block theme + companion plugin (talks, books, articles, interviews, projects CPTs via ACF Pro).

## Key contacts

- **Alex** - client

## Notes

- Local dev via VVV (`wp @alex-wright`)
- Production: SSH host alias `ssh_aw_host`, WP root `~/alexwright.com/docs`
- FSE templates/patterns pulled from production via `fse-pull-prd.sh`
- All tech access already in hand at onboarding (2026-10-12) - no access request sent
- staging.alexwright.com is Alex's static HTML mock-up, not WordPress - test updates on local VVV instead
- 2026-10-12: WP 6.9.10 -> 7.1.3 + plugin updates on production (AW-013); CF7/Really Simple CAPTCHA blocked on PHP 8.3
- Asana project: https://app.asana.com/1/512209774840/project/1211966443353563

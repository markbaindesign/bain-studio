---
tags:
- studio-project
prefix: JBP
name: Beato Properties
status: active
client: Jaume Beato
type: client
repo: git@ssh.bitbucket.org:markbaindesign/beato-properties.git
sector: Real Estate
stack: WordPress · Divi child theme · Estatik · WPML · FluentBooking · VVV · Cloudways
path: /media/data/dev/vvv/clients/www/beato-properties
asana: "yes"
qa: "yes"
client_docs: "/media/data/Dropbox/Work/Projects/Client/JBP Beato Properties"
inbox: "no"
open_tasks: 0
current_focus: "Listing location not saving in CA/ES; install-app prompt fix awaiting deploy"
next_action: "Deploy 1.2.1 (manifest + iOS title fix) once Mark gives the go-ahead"
---

# Beato Properties (JBP)

Client project. Trilingual (EN / CA / ES) real estate site for Jaume Beato, Catalonia South. Divi child theme `beato-properties` + custom plugin `beato-agents`, Estatik for listings. Local dev via VVV at `http://beato-properties.test/`. Staging and production on one Cloudways server.

## Key contacts

- **Jaume Beato**: client (jaume@beatoproperties.com)
- **Nicola Smith**: PM (nicola@beatoproperties.com), cc'd on client threads

## Asana

Studio-side tasks live on the bain.design "JBP Website" board (GID 1213078540273397). Client-facing task management happens on the client's own Asana board, which bainbot cannot reach.

## Deployment

Git flow (`develop` / `master`). Code goes out only via `scripts/deploy-code.sh`, with Mark's explicit approval for production. Non-code production changes are tracked in Dropbox `Dev Ops/production-change-register.md`.

## Notes

- See the project's own `CLAUDE.md` for CSS pipeline, WPML and Estatik conventions
- Shared server: staging work can affect production

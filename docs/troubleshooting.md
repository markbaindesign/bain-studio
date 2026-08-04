---
tags: [troubleshooting, studio]
description: Common studio tooling issues and their fixes
---

# Studio Troubleshooting

## Astro dev server serves stale CSS/JS after file edits (not fixed by hard refresh)

**Symptom:** Edit a `.astro` component's `<style>` or script, and the
change doesn't show up in the browser — including after a hard refresh.
Symptoms observed: a CSS rule you just added is entirely absent from
DevTools' Styles panel for that element, even though the attribute/class
it targets is correctly present in the live DOM.

**Cause:** Not browser caching, and not Astro's client-side View
Transitions/`ClientRouter` swap logic (traced through
`node_modules/astro/dist/transitions/swap-functions.js` — non-persisted
head/body elements are correctly replaced on every soft navigation).
Confirmed by `curl`ing the dev server directly (bypassing the browser
entirely): the **server itself** was returning HTML with stale inline
`<style data-vite-dev-id="...">` content that didn't match the source
file on disk. The long-running `astro dev` process's Vite file watcher
had stopped picking up changes for that file — happened on a dev server
that had been running continuously for ~1 hour across many edits (kf-tara-web,
2026-07-22).

**Fix:** Restart the dev server (`Ctrl+C`, then `npm run dev` again).
No code change needed — this is a stuck Vite watcher/process, not a bug
in the project.

**Diagnostic shortcut for next time:** before chasing browser-side
theories (cache, service worker, view transitions), rule out server-side
staleness first:

```bash
curl -s http://localhost:<port>/<page>/ | grep '<the CSS/text you just added>'
```

If that comes back empty while the source file on disk has the change,
the dev server itself is stale — restart it.

## Tasks exist in Asana but have no Local ID

**Symptom:** Tasks are visible in Asana but the Local ID custom field (e.g. `WTF-001`) is blank.

**Cause:** `--setup` was never run for the project, so `asana-ids.json` has `custom_field_gid: null` and sync can't write Local IDs back to Asana.

**Fix:** Run setup for the project, then sync:

```bash
python3 studio/sync.py --setup --project WTF
python3 studio/sync.py
```

Setup wires up the custom field GIDs; the following sync backfills Local IDs on all existing tasks.

## Tasks missing from Asana after project setup

**Symptom:** You set up a new project and tasks you expected are not visible in Asana.

**Cause:** `sync.py` is pull-only — it reads from Asana into the local mirror. It does not create new Asana tasks from mirror edits. If tasks were written directly into the mirror file, they will never appear in Asana.

**Fix:** Create tasks via the Asana API first. Once they exist in Asana, the next sync will pull them into the mirror.

```bash
python3 studio/sync.py
```

If tasks need to be seeded into a new project, use `/seed-tasks` or create them manually in Asana, then sync.

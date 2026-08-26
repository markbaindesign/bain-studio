---
tags: [tool, collector]
god: hermes
invoke: wp_pulse.py
description: Collates new posts across WordPress dev blogs into a summarised markdown digest, with a Slack ping
---

# wp_pulse

Watches a registry of WordPress development blogs, collects everything published since the last run, summarises the whole batch in a single headless Claude call, writes a dated markdown digest into the Obsidian vault, and pings Slack with the headlines.

Built to keep a finger on the pulse of the WordPress dev space without subscribing to a dozen newsletters. Each post gets a 2-3 sentence summary plus a `**Why it matters:**` line written against Mark's actual stack (Divi child themes, FSE/block themes, ACF Pro, WooCommerce, Cloudways, DDEV/VVV) - including an explicit "not relevant" where that is the honest answer.

## Usage

```bash
python3 studio/collectors/wp_pulse.py                      # collect, summarise, write digest, notify
python3 studio/collectors/wp_pulse.py --dry-run            # list what's new; no Claude call, no state written
python3 studio/collectors/wp_pulse.py --no-notify          # write the digest, skip the Slack ping
python3 studio/collectors/wp_pulse.py --since-days 30      # widen the lookback window for one run
python3 studio/collectors/wp_pulse.py --add "Name" "URL"   # add a feed
python3 studio/collectors/wp_pulse.py --list               # print the registry with last-checked state
python3 studio/collectors/wp_pulse.py --remove SLUG        # remove a feed
```

`--dry-run` writes no state, so it is always safe to run before a real pass.

## Files

- Registry: `studio/collectors/wp_pulse_sources.json` - the feeds being watched (committed)
- State: `studio/collectors/wp_pulse_state/{slug}.json` - per-source seen entry ids (gitignored)
- Digests: `$OBSIDIAN_VAULT/WP Pulse/YYYY-MM-DD-wp-pulse.md`
- Log: `studio/collectors/wp_pulse.log` (gitignored)

Digest destination falls back through `WP_PULSE_DIGEST_DIR` → `$OBSIDIAN_VAULT/WP Pulse/` → `studio/collectors/wp_pulse_digests/`. A second run on the same day appends a `## Later run - HH:MM` section rather than overwriting the earlier digest.

## Schedule

Twice weekly, Monday and Thursday at 08:25 (after the other morning collectors):

```
25 8 * * 1,4 cd /media/data/dev/bain-studio && python3 studio/collectors/wp_pulse.py >> studio/collectors/wp_pulse.log 2>&1
```

## Verifying under cron

Hand-running proves the code works; it does **not** prove the job works under cron. Cron uses a minimal environment - no profile is sourced, and `PATH` is whatever the crontab sets. Any collector that shells out to `claude` is exposed to this.

Reproduce cron's environment before trusting a new schedule:

```bash
env -i HOME="$HOME" PATH=/home/bain/.local/bin:/home/bain/.nvm/versions/node/v22.23.1/bin:/usr/local/bin:/usr/bin:/bin \
  bash -c 'cd /media/data/dev/bain-studio && python3 studio/collectors/wp_pulse.py --dry-run'
```

This is a one-time check per scheduled job, not per code change.

The crontab sets `PATH` explicitly because cron's default (`/usr/bin:/bin`) contains neither `claude` (`~/.local/bin`) nor `node` (nvm). Before that line was added on 2026-08-26, `gmail_watch` had failed on every run since 2026-05-26 - 90 consecutive `FileNotFoundError: 'claude'` crashes, invisible because the failure only ever reached a log file.

Note the node entry is nvm-version-pinned (`v22.23.1`) and will need updating when node is upgraded. Without it `claude` still runs, but its `SessionEnd` hook fails noisily.

## Default sources

Seeded on first run, all verified as serving valid RSS/Atom:

| Source | Feed |
|---|---|
| GeneratePress | `generatepress.com/blog/feed/` |
| WP Tavern | `wptavern.com/feed` |
| WordPress News | `wordpress.org/news/feed/` |
| Make WordPress Core | `make.wordpress.org/core/feed/` |
| Make WordPress Design | `make.wordpress.org/design/feed/` |
| WordPress Developer Blog | `developer.wordpress.org/news/feed/` |
| Post Status | `poststatus.com/feed/` |
| Advanced Custom Fields | `advancedcustomfields.com/blog/feed/` |
| Elegant Themes (Divi) | `elegantthemes.com/blog/feed` |
| Kinsta | `kinsta.com/blog/feed/` |
| Delicious Brains | `deliciousbrains.com/feed/` |
| WP Mayor | `wpmayor.com/feed/` |
| Smashing Magazine (WordPress) | `smashingmagazine.com/category/wordpress/feed/` |

Two candidates were rejected during setup: `wpengine.com/blog/feed/` (404) and `gravitywp.com/feed/` (403 to non-browser clients).

## How it works

Feeds are parsed with the standard library, handling both RSS 2.0 and Atom, so the only dependency is `requests` - already used by the other collectors. Entries are deduplicated on `guid`/Atom `id`, falling back to the post URL.

- **Lookback window** (`DEFAULT_LOOKBACK_DAYS`, 14): posts older than the window are marked seen without being summarised. This is what stops the very first run digesting a decade of back-catalogue.
- **Per-source cap** (`MAX_ENTRIES_PER_SOURCE`, 12): a source is limited to 12 posts per digest. Anything over the cap is *not* marked seen, so it rolls into the next run rather than being lost.
- **Undated entries are kept**, not dropped - some feeds omit `pubDate`, and skipping them would silently hide a source.
- **State is written before summarising**, so a crash mid-run costs one digest rather than replaying the same posts forever.
- **One Claude call per run**, not per post. Only a `EXCERPT_CHARS` (700) excerpt of each post is sent, which is enough to summarise and keeps the batch cheap.

## Cost

Measured on the first run, 2026-08-26: **$0.59 for 42 posts**. That was an unusually large batch (a 14-day cold start across 13 sources). A steady-state twice-weekly run of 10-15 posts costs roughly $0.15-0.25, so about **$1.50/month**.

If that needs trimming: drop the high-volume, low-relevance sources first (Elegant Themes posts near-daily; Smashing Magazine's WordPress category is broad), or lower `EXCERPT_CHARS`.

## Known quiet sources

At setup, Post Status, Delicious Brains, and Make WordPress Design had published nothing in the preceding 14 days. Their feeds are live and parse correctly, so they are kept in the registry - but if they show `0 new` for months on end, they are candidates for `--remove`.

## Source

`studio/collectors/wp_pulse.py`

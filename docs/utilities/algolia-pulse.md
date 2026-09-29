---
tags: [tool, collector, devops]
god: hermes
invoke: .claude/skills/algolia-pulse/algolia_pulse.py
command: /algolia-pulse
description: Keeps Algolia free-tier search indices alive by querying them weekly via cron and posting a Slack summary, preventing auto-closure of inactive apps
---

# algolia-pulse

Algolia closes free-tier apps after extended inactivity. **Algolia Pulse** performs a
lightweight search query against each configured index on a weekly cron, so client sites
running the free tier never go dark from disuse rather than from an actual problem.

## Usage

```bash
python3 .claude/skills/algolia-pulse/algolia_pulse.py --config ~/.algolia/pulse-config.json [--dry-run] [--verbose] [--no-notify]
```

- `--config PATH` (required): JSON file listing apps, admin API keys, and indices to query
- `--dry-run`: validate the config and print what would be queried, without calling the API
- `--verbose`: print per-index results
- `--no-notify`: skip the Slack summary (use when testing by hand)

Config format and full setup instructions live in
`.claude/skills/algolia-pulse/SKILL.md`.

## Dependency

Uses the `algoliasearch` PyPI package, **v4** client (`algoliasearch.search.client.SearchClientSync`,
`search_single_index`). The package's v2/v3 API (`SearchClient.create()` / `init_index()`) is gone in v4 -
if this script is ever reworked, don't reintroduce that import path.

## Slack summary

Every real run (not `--dry-run`) posts one message to the studio Slack channel via
`studio/notifier.py` (`SLACK_WEBHOOK_URL` in `studio/.env`, sender `algolia-pulse`, project `BSTD`):

- all indices OK: a low-priority line, `Algolia Pulse: 33/33 indices OK across 5 apps`, with a
  per-app breakdown
- any failure: a high-priority `N of M indices FAILED`, listing each failed index by app

The notifier never raises, so a Slack outage cannot fail the pulse or change its exit code.

## Scheduling

Runs weekly, Mondays at 07:00 via the studio crontab, from the `main`-tracked ops checkout
(`/home/bain/ops/bain-studio`), logging to `~/.algolia/pulse-cron.log`:

```
0 7 * * 1 python3 /home/bain/ops/bain-studio/.claude/skills/algolia-pulse/algolia_pulse.py --config $HOME/.algolia/pulse-config.json >> $HOME/.algolia/pulse-cron.log 2>&1
```

Because studio cron always runs off `main`, any future fix to this script needs a
`hotfix/x.y.z` branch (per the studio's git flow, not a feature/bugfix branch off `develop`)
so it reaches the ops checkout without waiting for a full release cycle.

## Config

Lives at `~/.algolia/pulse-config.json` (mode 600, gitignored path, contains live admin API
keys - never commit it). Pulse only runs search queries, so the `admin_api_key` field can
hold a **search-only** key (it is just the field name the script reads); prefer that for apps
where you have one, since it limits the damage if the file leaks. One entry per app, each with its indices and a search query
(`"*"` is fine - the point is just to register activity, not to validate results).

## Known gaps

- Credentials for client Algolia apps are scattered across each WordPress project's
  `wp-config.php` (`ALGOLIA_APPLICATION_ID` / `ALGOLIA_API_KEY` per environment) - there is no
  central registry. When onboarding a new app, check the project's `wp-config.php` for all
  three environment blocks (local/staging/production) - some apps may already be blocked or
  gone, which the pulse can't detect or fix, only prevent.
- The WP Search with Algolia plugin can also store its keys as DB options rather than
  wp-config constants, which a wp-config sweep won't catch.
</content>

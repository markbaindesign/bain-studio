---
name: algolia-pulse
description: Keeps Algolia free-tier search indices alive by querying them periodically. Prevents auto-closure of inactive indices. Configure via JSON file with app credentials, attach to cron for automated runs.
allowed-tools: [Bash, Read, Write]
---

# Algolia Pulse

Algolia automatically closes free-tier indices after extended inactivity. **Algolia Pulse** keeps indices alive by performing regular search queries. It's lightweight, cheap (counts toward API quota but not metered), and can be scheduled to run daily or hourly via cron.

---

## Setup

### 1. Create the config file

Create a JSON file with your Algolia app credentials. Suggested location:
```
~/.algolia/pulse-config.json
```

Or keep it in a project-specific location, e.g.:
```
/media/data/dev/bain-studio/studio/algolia-pulse-config.json
```

Config format:

```json
{
  "apps": [
    {
      "name": "example-app-1",
      "app_id": "YOUR_APP_ID",
      "admin_api_key": "YOUR_ADMIN_API_KEY",
      "indices": [
        {
          "name": "products",
          "query": "*"
        },
        {
          "name": "blog",
          "query": "a"
        }
      ]
    },
    {
      "name": "example-app-2",
      "app_id": "ANOTHER_APP_ID",
      "admin_api_key": "ANOTHER_API_KEY",
      "indices": [
        {
          "name": "posts",
          "query": "*"
        }
      ]
    }
  ]
}
```

**Fields:**
- `name`: Friendly name for the app (for logging)
- `app_id`: Algolia Application ID
- `admin_api_key`: Algolia Admin API Key (needed for search operations)
- `indices`: Array of indices to query
  - `name`: Index name
  - `query`: Search query to perform (e.g., `"*"` for any record, `"a"` for a simple letter query)

### 2. Test the config

```bash
/algolia-pulse --config ~/.algolia/pulse-config.json --dry-run
```

This validates the config and shows which queries would be run without actually running them.

---

## Invoke

```bash
/algolia-pulse --config /path/to/pulse-config.json [--dry-run] [--verbose]
```

**Arguments:**
- `--config PATH` (required): Path to the JSON config file
- `--dry-run`: Validate config and show what would be queried without running
- `--verbose`: Show detailed output for each query

---

## How it works

1. Read the config file
2. Validate app credentials and index names
3. For each app and index, perform the configured search query
4. Log results to `~/.algolia/pulse.log` (rotated daily)
5. Output summary: `{N} apps, {M} indices queried successfully`

---

## Scheduling with cron

To keep indices alive, run Algolia Pulse daily or hourly:

```bash
# Daily at 09:00
0 9 * * * /usr/bin/python3 -c "import subprocess; subprocess.run(['claude', '--dangerously-skip-permissions', '-p', '/algolia-pulse --config ~/.algolia/pulse-config.json'], cwd='/media/data/dev/bain-studio')"

# Hourly
0 * * * * /usr/bin/python3 -c "import subprocess; subprocess.run(['claude', '--dangerously-skip-permissions', '-p', '/algolia-pulse --config ~/.algolia/pulse-config.json'], cwd='/media/data/dev/bain-studio')"
```

Or use the `/schedule` skill to set up a recurring run:

```bash
/schedule --cron "0 9 * * *" --command "/algolia-pulse --config ~/.algolia/pulse-config.json"
```

---

## Example: Adding a new app

If you've added a new Algolia app:

1. Get the app credentials from https://dashboard.algolia.com
2. Add an entry to `pulse-config.json`
3. Test with `--dry-run`
4. Restart the cron job if already scheduled

---

## Logs

Logs are written to `~/.algolia/pulse.log`. Each run records:
- Timestamp
- App name
- Index name
- Query executed
- Result (success/failure)
- Response time

Check logs to verify runs are happening:
```bash
tail -f ~/.algolia/pulse.log
```

---

## Troubleshooting

**"Config file not found"**
- Check the path: `ls -la /path/to/pulse-config.json`
- Ensure file exists and is readable

**"Invalid credentials"**
- Check app ID and API key in https://dashboard.algolia.com
- Verify the API key has "Search" permissions (should be the Admin key)

**"Index not found"**
- Verify index name spelling in Algolia dashboard
- Check that the index isn't in a different app

**Cron job not running**
- Check cron logs: `grep CRON /var/log/syslog` (Linux) or `log stream --predicate 'process=="cron"'` (macOS)
- Verify paths are absolute (not relative)
- Test manually: run the command outside cron first

---

## Notes

- **Free tier**: Algolia free plans have a monthly API call quota. Pulse queries count toward this. A daily query per index ≈ 30 calls/month — well within free limits.
- **Response time**: Each query is fast (<100ms on most indices). Pulse adds minimal overhead.
- **Inactive threshold**: Algolia's closure threshold varies by plan; free-tier indices can close after weeks/months without queries. Running Pulse daily keeps them alive indefinitely.
- **No write operations**: Pulse only performs searches, never modifies data. Safe to run anytime.

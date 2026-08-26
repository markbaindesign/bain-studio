#!/usr/bin/env bash
#
# Link the ops worktree's runtime state to the canonical dev checkout.
#
# The ops worktree (pinned to main, run by cron) is a fresh checkout of TRACKED
# files only. Everything gitignored - secrets, collector state, Asana mirrors,
# logs - does not come across. Without these links each collector would keep a
# second, divergent copy of its state, and wp_pulse would re-digest posts the
# dev tree had already seen.
#
# Every path below is symlinked back to the dev checkout so there is exactly one
# copy of each. Safe to re-run: existing symlinks are refreshed, real files are
# never clobbered.
#
# Usage:
#   studio/scripts/ops-worktree-link.sh [OPS_DIR]     # default /home/bain/ops/bain-studio
#   studio/scripts/ops-worktree-link.sh --check       # report only, change nothing

set -euo pipefail

SRC="/media/data/dev/bain-studio"
OPS="${1:-/home/bain/ops/bain-studio}"
CHECK=0
[ "${1:-}" = "--check" ] && { CHECK=1; OPS="/home/bain/ops/bain-studio"; }

# Gitignored runtime paths that must be shared, not duplicated.
PATHS=(
  # secrets and config
  "studio/.env"
  "studio/projects.json"
  "studio/tools/ivas-prep/credentials.json"
  "studio/tools/cloudways-mcp-server/.env"

  # collector state - the reason duplication would be a correctness bug
  "studio/.gmail_state.json"
  "studio/collectors/careers_watch_state"
  "studio/collectors/wp_pulse_state"
  "studio/collectors/obsidian_collector_state.json"
  "studio/collectors/obsidian_standup.json"
  "studio/collectors/obsidian_tagged_items.json"

  # Asana mirrors - sync.py reads and writes these
  "asana-mirror.md"
  "asana-ids.json"
  "studio/looper/asana-mirror.md"
  "studio/looper/asana-ids.json"
  "studio/looper-test/asana-mirror.md"
  "studio/looper-test/asana-ids.json"

  # inbox - hermes routes messages out of here
  "studio/inbox"

  # logs - keep one place to look, in the dev checkout
  "studio/sync.log"
  "studio/postman.log"
  "studio/collectors/careers_watch.log"
  "studio/collectors/gmail_watch.log"
  "studio/collectors/gnucash_collector.log"
  "studio/collectors/harvest_kf_collector.log"
  "studio/collectors/hermes.log"
  "studio/collectors/obsidian_collector.log"
  "studio/collectors/wp_pulse.log"
  "studio/scripts/account_forecast_report.log"
)

if [ ! -d "$OPS" ]; then
  echo "ERROR: ops worktree not found at $OPS" >&2
  echo "Create it first:  git -C $SRC worktree add $OPS main" >&2
  exit 1
fi

linked=0; skipped=0; missing=0; problems=0

for rel in "${PATHS[@]}"; do
  src="$SRC/$rel"
  dst="$OPS/$rel"

  if [ ! -e "$src" ]; then
    printf '  %-52s source missing, skipped\n' "$rel"
    missing=$((missing + 1))
    continue
  fi

  # Already correctly linked
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    skipped=$((skipped + 1))
    continue
  fi

  # A real file here means the ops tree grew its own divergent copy. Never
  # silently delete it - that is someone's data.
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    printf '  %-52s REAL FILE PRESENT - not touching\n' "$rel"
    problems=$((problems + 1))
    continue
  fi

  if [ "$CHECK" = "1" ]; then
    printf '  %-52s would link\n' "$rel"
    linked=$((linked + 1))
    continue
  fi

  mkdir -p "$(dirname "$dst")"
  rm -f "$dst"
  ln -s "$src" "$dst"
  printf '  %-52s linked\n' "$rel"
  linked=$((linked + 1))
done

echo
echo "linked=$linked  already-ok=$skipped  source-missing=$missing  conflicts=$problems"

if [ "$problems" -gt 0 ]; then
  echo
  echo "Some paths hold real files in the ops worktree rather than symlinks." >&2
  echo "Inspect them, move anything worth keeping into $SRC, then re-run." >&2
  exit 2
fi

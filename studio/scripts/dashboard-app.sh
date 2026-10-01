#!/usr/bin/env bash
# Open the studio dashboard as a standalone Chromium app window.
# Starts the Flask server first if nothing is listening on 5555.
set -u
URL=http://localhost:5555
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

if ! curl -s -o /dev/null "$URL"; then
  (cd "$REPO" && nohup python3 studio/dashboard/server.py >/dev/null 2>&1 &)
  for _ in $(seq 1 30); do
    curl -s -o /dev/null "$URL" && break
    sleep 0.5
  done
fi

exec chromium --app="$URL" --class=studio-dashboard

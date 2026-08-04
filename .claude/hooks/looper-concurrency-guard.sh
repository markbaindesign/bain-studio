#!/bin/bash
# Mechanically enforce the studio-looper concurrency guard (Step 1a of
# .claude/skills/studio-looper/SKILL.md) — belt-and-braces enforcement, same rationale
# as looper-no-push.sh: prose guard rails are not enforcement, especially on cheaper
# models. An eval caught the agent (headless, --model haiku) misclassifying a LIVE
# conflict as stale and clearing it anyway (2026-07-22) — this hook makes that
# impossible regardless of what the agent concludes, by independently re-running the
# exact tested classification logic (studio/scripts/looper_logic.py) and denying the
# tool call outright when it disagrees.
#
# Covers the two ways an agent can violate the guard:
#   1. Write — creating a NEW /tmp/studio-looper/studio-looper.*.local.md state file
#      (Step 3) while another file for the same target_prefix is genuinely LIVE.
#   2. Bash rm — deleting an EXISTING state file that is genuinely LIVE (the failure
#      mode the eval caught: agent decides to "clear" a file it shouldn't).
#
# Versioned at bain-studio/.claude/hooks/looper-concurrency-guard.sh; referenced by
# absolute path from ~/.claude/settings.json so it fires in any cwd.

STUDIO="/media/data/dev/bain-studio"
LOOPER_LOGIC="$STUDIO/studio/scripts/looper_logic.py"
STATE_DIR="/tmp/studio-looper"
STATE_FILE_RE="studio-looper\.[A-Za-z0-9_.-]+\.local\.md"
TASK_LOG="$HOME/logs/task-looper.log"

input=$(cat)

deny() {
  local reason="$1"
  mkdir -p "$(dirname "$TASK_LOG")"
  echo "$(date '+%Y-%m-%d %H:%M:%S') WARN    [hook] looper-concurrency-guard denied a tool call: $reason" >> "$TASK_LOG"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
  exit 0
}

file_path=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('file_path', ''))
except Exception:
    pass
" 2>/dev/null)

# --- Case 1: Write of a new looper state file ---------------------------------
if [ -n "$file_path" ] && [[ "$file_path" =~ $STATE_FILE_RE ]]; then
  content=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('content', ''))
except Exception:
    pass
" 2>/dev/null)

  target_prefix=$(printf '%s' "$content" | grep -m1 '^target_prefix:' | sed 's/target_prefix: *//' | tr -d '\r')
  [ -z "$target_prefix" ] && target_prefix="SL"

  live=$(python3 "$LOOPER_LOGIC" concurrency "$target_prefix" 2>/dev/null | grep '^LIVE:' | head -1)
  if [ -n "$live" ]; then
    # Fields are colon-joined but the deadline itself contains colons (ISO timestamp),
    # so a naive `cut -d:` misparses. session/current_task never contain colons, so
    # pull them from the right end instead.
    read -r conflict_session conflict_task <<< "$(echo "$live" | python3 -c "
import sys
parts = sys.stdin.read().strip().split(':')
print(parts[-2], parts[-1])
")"
    deny "Blocked by looper-concurrency-guard hook: a LIVE run already targets [$target_prefix] (session $conflict_session, working $conflict_task). Refusing to start a second run against the same queue — wait for it to finish or use --test against the SLT sandbox instead."
  fi
  exit 0
fi

# --- Case 2: Bash command deleting a looper state file ------------------------
cmd=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception:
    pass
" 2>/dev/null)

[ -z "$cmd" ] && exit 0
if ! echo "$cmd" | grep -qE '(^|[;&| ])rm '; then
  exit 0
fi

target=$(echo "$cmd" | grep -oE "$STATE_DIR/$STATE_FILE_RE" | head -1)
[ -z "$target" ] && exit 0

status=$(python3 "$LOOPER_LOGIC" check-path "$target" 2>/dev/null)
if [ "$status" = "LIVE" ]; then
  deny "Blocked by looper-concurrency-guard hook: $target is currently LIVE (deadline not passed, touched within the inactivity window) — deleting it would silently let a second run collide with a genuinely active one. If this file is truly dead, check ~/logs/task-looper.log by hand before removing it."
fi

exit 0

#!/bin/bash
# Hard-block `git push` (and force variants) in studio-looper sessions.
# Belt-and-braces enforcement of the skill's "never push the review branch"
# rule (ADR 009) — prose guard rails are not enforcement, especially on
# cheaper models.
#
# Armed when EITHER:
#   - LOOPER_RUN_ID is set (exported by looper_runner.py), or
#   - this session owns a looper state file in /tmp/studio-looper/ (written by
#     the studio-looper skill at Step 3 of every run, manual or scheduled).
# The second condition closes the gap that let a manually launched
# /studio-looper push develop on 2026-07-22: only runner launches were armed.
# Interactive non-looper sessions have neither and are unaffected.
#
# Versioned at bain-studio/.claude/hooks/looper-no-push.sh; referenced by
# absolute path from ~/.claude/settings.json so it fires in any cwd.

input=$(cat)

armed=""
if [ -n "$LOOPER_RUN_ID" ]; then
  armed="$LOOPER_RUN_ID"
else
  sid=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('session_id', ''))
except Exception:
    pass
" 2>/dev/null)
  if [ -n "$sid" ] && [ -f "/tmp/studio-looper/studio-looper.${sid}.local.md" ]; then
    armed="${sid:0:8}"
  fi
fi

[ -z "$armed" ] && exit 0

cmd=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    pass
")

if echo "$cmd" | grep -qE '(^|[;&| ])git ([^;&|]* )?push'; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Blocked by looper-no-push hook: looper sessions never push. Work stays on the local looper/%s branch for Mark'\''s review. If the task cannot complete without pushing, mark it Blocked."}}\n' "$armed"
fi

exit 0

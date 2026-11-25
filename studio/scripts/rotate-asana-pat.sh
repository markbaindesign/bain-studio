#!/usr/bin/env bash
# Rotate the bainbot Asana personal access token across every live location.
#
# Why a script: the token is held in four separate live files plus stale
# backups. Missing one breaks the scheduled syncs silently, hours later.
#
# The new token is read from the terminal with `read -rs`. It is never passed
# as an argument, never echoed, and never written to a backup copy — the
# current token spread across transcripts, shell history and editor history is
# the direct result of a credential travelling through those channels.
#
# Run it yourself, in your own terminal. Do not run it inside a Claude session:
# anything typed at a session prompt is recorded in that session's transcript.
#
# Usage:
#   studio/scripts/rotate-asana-pat.sh --check    # report where the current token lives
#   studio/scripts/rotate-asana-pat.sh            # rotate
#
# See docs/utilities/rotate-asana-pat.md.

set -euo pipefail
set +x

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$REPO/studio/.env"

# Live locations that must carry the token after rotation.
TARGETS=(
  "$ENV_FILE"
  "$HOME/.claude/settings.json"
  "$HOME/.claude-kf/settings.json"
)

# Superseded credential backups, deleted rather than left holding a dead secret.
STALE_GLOBS=(
  "$HOME/.claude/settings.json.bak"*
  "$HOME/.claude-kf/settings.json.bak"*
)

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

[[ -f "$ENV_FILE" ]] || die "no studio/.env at $ENV_FILE"

OLD="$(python3 -I -c '
import sys
for line in open(sys.argv[1], encoding="utf-8"):
    if line.startswith("ASANA_PAT"):
        print(line.split("=", 1)[1].strip().strip("\"").strip("\x27"))
        break
' "$ENV_FILE")"
[[ -n "$OLD" ]] || die "ASANA_PAT not set in studio/.env"

# Count occurrences of $1 in a file without printing any part of it.
count_in() {
  python3 -I -c '
import sys
needle, path = sys.argv[1], sys.argv[2]
try:
    print(open(path, encoding="utf-8", errors="replace").read().count(needle))
except FileNotFoundError:
    print(-1)
' "$1" "$2"
}

report() {
  local needle="$1" label="$2" path n missing=0
  printf '%s:\n' "$label"
  for path in "${TARGETS[@]}"; do
    n="$(count_in "$needle" "$path")"
    case "$n" in
      -1) printf '  absent file  %s\n' "$path" ;;
       0) printf '  0 matches    %s\n' "$path"; missing=$((missing + 1)) ;;
       *) printf '  %s match(es)   %s\n' "$n" "$path" ;;
    esac
  done
  return 0
}

if [[ "${1:-}" == "--check" ]]; then
  report "$OLD" "Current token, live locations"
  printf '\nStale credential backups on disk:\n'
  for f in "${STALE_GLOBS[@]}"; do [[ -e "$f" ]] && printf '  %s\n' "$f"; done
  printf '\nThese are not touched by rotation and do not need to be: rotation is\n'
  printf 'what makes them harmless.\n\n'
  printf 'Dead copies of it elsewhere on disk:\n'
  printf '%s\n' "$OLD" | grep -rlIF -f - \
    "$HOME/.claude" "$HOME/.claude-kf" "$HOME/.config/Code/User/History" 2>/dev/null \
    | sed 's#^#  #' || true
  exit 0
fi

printf 'Rotating the bainbot Asana PAT.\n\n'
report "$OLD" "Before"

printf '\nGenerate a new token in the bainbot Asana account first, under\n'
printf 'Settings -> Apps -> Personal Access Tokens. Asana allows several at\n'
printf 'once, so do NOT revoke the old one yet: every scheduled sync between\n'
printf 'the revoke and this script failing is downtime for nothing. Revoke it\n'
printf 'after this finishes.\n\n'
printf 'Paste the new token (not echoed): '
read -rs NEW
printf '\n\n'
[[ -n "$NEW" ]] || die "no token entered"
[[ "$NEW" != "$OLD" ]] || die "that is the current token, not a new one"
[[ "$NEW" =~ ^2/[0-9]+(/[0-9]+)?:[A-Za-z0-9]+$ ]] || die "that does not look like an Asana PAT"

# Prove the new token works before a single file is touched: a half-rotated
# set of files with a bad token is worse than none.
# Asana's token page does not show which account a PAT belongs to, so ask the
# API. A token for the wrong account authenticates perfectly and then writes to
# Asana under the wrong name, which is the failure the bainbot account exists
# to prevent.
printf 'Asking Asana which account this token belongs to...\n'
WHO="$(NEW="$NEW" python3 -I -c '
import json, os, sys, urllib.error, urllib.request
req = urllib.request.Request(
    "https://app.asana.com/api/1.0/users/me",
    headers={"Authorization": "Bearer " + os.environ["NEW"]})
try:
    d = json.load(urllib.request.urlopen(req, timeout=20))["data"]
except urllib.error.HTTPError as e:
    print("HTTP %s" % e.code); sys.exit(0)
except Exception as e:
    print("unreachable: %s" % e); sys.exit(0)
print("%s|%s|%s" % (d.get("name"), d.get("email"), d.get("gid")))
')"

case "$WHO" in
  *"|"*"|"*) ;;
  *) die "could not authenticate the new token ($WHO); nothing was changed" ;;
esac

printf '  name:  %s\n' "${WHO%%|*}"
printf '  email: %s\n' "$(printf '%s' "$WHO" | cut -d'|' -f2)"
printf '  gid:   %s\n\n' "${WHO##*|}"

CUR="$(OLD="$OLD" python3 -I -c '
import json, os, urllib.error, urllib.request
req = urllib.request.Request(
    "https://app.asana.com/api/1.0/users/me",
    headers={"Authorization": "Bearer " + os.environ["OLD"]})
try:
    print(json.load(urllib.request.urlopen(req, timeout=20))["data"].get("gid"))
except Exception:
    print("")
')"

if [[ -n "$CUR" && "$CUR" != "${WHO##*|}" ]]; then
  printf 'WARNING: the token in use belongs to account %s, this one to %s.\n' \
    "$CUR" "${WHO##*|}"
  printf 'Different accounts means every task and comment would appear under a\n'
  printf 'different name in Asana. Continue anyway? [y/N] '
  read -r acct
  [[ "$acct" == [yY] ]] || die "stopped; nothing was changed"
  printf '\n'
fi

swap() {
  local path="$1"
  [[ -f "$path" ]] || { printf '  skipped (absent)  %s\n' "$path"; return 0; }
  OLD="$OLD" NEW="$NEW" python3 -I -c '
import os, sys, pathlib
old, new = os.environ["OLD"], os.environ["NEW"]
p = pathlib.Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
if old not in text:
    print("  no match, left alone  %s" % p); sys.exit(0)
# Written in place with no .bak: a backup of a credential file is how the
# stale copies this rotation is cleaning up came to exist.
p.write_text(text.replace(old, new), encoding="utf-8")
print("  updated  %s" % p)
' "$path"
}

printf 'Updating live locations:\n'
for t in "${TARGETS[@]}"; do swap "$t"; done

printf '\nTightening permissions on the files that hold it:\n'
for t in "${TARGETS[@]}"; do
  if [[ -f "$t" ]]; then chmod 600 "$t"; printf '  0600  %s\n' "$t"; fi
done

printf '\nStale credential backups:\n'
found=0
for f in "${STALE_GLOBS[@]}"; do
  if [[ -e "$f" ]]; then printf '  %s\n' "$f"; found=$((found + 1)); fi
done
if (( found )); then
  printf 'Delete these %d file(s)? They hold the now-dead token. [y/N] ' "$found"
  read -r reply
  if [[ "$reply" == [yY] ]]; then
    for f in "${STALE_GLOBS[@]}"; do [[ -e "$f" ]] && rm -f -- "$f" && printf '  deleted  %s\n' "$f"; done
  else
    printf '  left in place\n'
  fi
else
  printf '  none\n'
fi

printf '\nVerifying:\n'
report "$OLD" "Old token, live locations (expect 0 everywhere)"
report "$NEW" "New token, live locations (expect 1 each)"

printf '\nThe token itself was already proved against the API above, before any\n'
printf 'file was written. To confirm sync.py picks it up, read any task:\n'
printf '  python3 studio/sync.py --get-task "$(python3 studio/registry.py --prefix BSTD --field gid)"\n'

printf '\nDone. Two things left, neither of them automatic:\n'
printf '  - Revoke the old token in the Asana account it belongs to. Until you\n'
printf '    do, every dead copy on disk is still a working credential.\n'
printf '  - Decide whether the two settings.json files should hold a token at\n'
printf '    all. An env entry there loads into every session context, which is\n'
printf '    how the old one reached transcripts and a memory file (BSTD-814).\n'

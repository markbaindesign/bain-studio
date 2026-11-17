#!/usr/bin/env bash
# Point git at the repo's versioned hooks, and check this machine can actually
# run the client-data guard.
#
# Run once per clone. core.hooksPath is per-clone, so a new worktree-bearing
# checkout needs it too.
#
#   studio/scripts/setup-machine.sh
#
# See CLAUDE.md "No client data. Ever.", ADR 021, BSTD-875.
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

echo "setup-machine: $ROOT"

git config core.hooksPath studio/hooks
echo "  ✓ core.hooksPath = studio/hooks (pre-commit, commit-msg)"

REGISTRY="${BAIN_REGISTRY:-${XDG_DATA_HOME:-$HOME/.local/share}/bain-studio/registry.json}"
if python3 studio/scripts/gen-denylist.py >/dev/null 2>&1; then
  n=$(python3 studio/scripts/gen-denylist.py | wc -l)
  echo "  ✓ registry readable, $n denylist terms"
else
  cat >&2 <<EOF
  ✗ the client-data guard cannot run on this machine.

    No usable registry at:
      $REGISTRY

    Until it exists, EVERY commit here is refused — deliberately. An
    unconfigured machine is where client data slips through unnoticed.

    Fix it by copying the registry from a machine that has one, then re-run
    this script. The registry is not in this repo and must not be: it names
    clients, and this repo is public.

    For a deliberate one-off commit meanwhile:
      BAIN_SKIP_CLIENT_GUARD=1 git commit ...
EOF
  exit 1
fi

if [ -f studio/.env ]; then
  echo "  ✓ studio/.env present"
else
  echo "  ! studio/.env missing — copy studio/.env.example and fill it in"
fi

echo
echo "Check the tree at any time:"
echo "  git grep -lIiwF -f <(python3 studio/scripts/gen-denylist.py) -- . ':!CHANGELOG.md'"

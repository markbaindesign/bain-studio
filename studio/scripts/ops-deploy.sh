#!/usr/bin/env bash
#
# Deploy a released version to the ops worktree that cron runs from.
#
# The ops worktree sits on a DETACHED HEAD at a release tag, deliberately - not
# on the `main` branch. Two reasons:
#
#   1. git flow needs `main`. `git flow release finish` runs
#      `git checkout main || die`, which fails if any worktree holds that branch.
#      Keeping ops detached leaves `main` free in the dev checkout.
#   2. A tag is a stronger promise than a branch. Cron runs an explicit, named
#      version rather than "whatever main happens to point at right now", and
#      deployment becomes a deliberate act with an obvious rollback.
#
# Usage:
#   studio/scripts/ops-deploy.sh              # deploy the latest release tag
#   studio/scripts/ops-deploy.sh 1.2.0        # deploy a specific tag (also how you roll back)
#   studio/scripts/ops-deploy.sh --check      # report current vs latest, change nothing

set -euo pipefail

SRC="/media/data/dev/bain-studio"
OPS="${OPS_DIR:-/home/bain/ops/bain-studio}"
LINK_SCRIPT="$SRC/studio/scripts/ops-worktree-link.sh"

CHECK=0
TARGET=""
case "${1:-}" in
  --check) CHECK=1 ;;
  "")      ;;
  *)       TARGET="$1" ;;
esac

if [ ! -d "$OPS" ]; then
  echo "ERROR: ops worktree not found at $OPS" >&2
  echo "Create it:  git -C $SRC worktree add --detach $OPS <tag>" >&2
  exit 1
fi

git -C "$SRC" fetch --tags --quiet origin 2>/dev/null || \
  echo "WARN: could not fetch from origin, using local tags" >&2

# Newest tag by version order, not commit date - a hotfix cut from an older
# branch must not be treated as newer than the release it patches.
LATEST=$(git -C "$SRC" tag --sort=-version:refname | head -1)
[ -n "$TARGET" ] || TARGET="$LATEST"

if ! git -C "$SRC" rev-parse -q --verify "refs/tags/$TARGET" >/dev/null; then
  echo "ERROR: no such tag: $TARGET" >&2
  echo "Available: $(git -C "$SRC" tag --sort=-version:refname | head -5 | paste -sd' ')" >&2
  exit 1
fi

# Show the commits between where ops is and where it is going, in whichever
# direction that happens to be. A rollback must list what it removes, not print
# an empty list because the range only reads forwards.
show_delta() {
  local from="$1" to="$2"
  if [ -n "$(git -C "$SRC" log --oneline "$from".."$to" 2>/dev/null)" ]; then
    echo "Changes being deployed:"
    git -C "$SRC" log --oneline "$from".."$to" | sed 's/^/  + /' | head -20
  elif [ -n "$(git -C "$SRC" log --oneline "$to".."$from" 2>/dev/null)" ]; then
    echo "ROLLBACK - these commits will no longer be live:"
    git -C "$SRC" log --oneline "$to".."$from" | sed 's/^/  - /' | head -20
  else
    echo "(no commit difference)"
  fi
}

CURRENT_SHA=$(git -C "$OPS" rev-parse HEAD)
TARGET_SHA=$(git -C "$OPS" rev-parse "$TARGET^{commit}")
CURRENT_DESC=$(git -C "$OPS" describe --tags --exact-match HEAD 2>/dev/null || echo "${CURRENT_SHA:0:8} (untagged)")

echo "ops worktree : $OPS"
echo "currently at : $CURRENT_DESC"
echo "latest tag   : $LATEST"
echo "deploying    : $TARGET"
echo

if [ "$CURRENT_SHA" = "$TARGET_SHA" ]; then
  echo "Already at $TARGET - nothing to deploy."
  [ "$CHECK" = "1" ] && exit 0
  echo "Re-running link check anyway:"
  "$LINK_SCRIPT" --check | tail -1
  exit 0
fi

if [ "$CHECK" = "1" ]; then
  echo "Would deploy $TARGET (currently $CURRENT_DESC)."
  show_delta "$CURRENT_SHA" "$TARGET_SHA"
  exit 0
fi

# A dirty ops tree means something wrote into it that should not have. Stop
# rather than discarding it - tracked files there are never edited by hand.
if [ -n "$(git -C "$OPS" status --porcelain --untracked-files=no)" ]; then
  echo "ERROR: ops worktree has uncommitted changes to tracked files:" >&2
  git -C "$OPS" status --short --untracked-files=no >&2
  echo "Investigate before deploying - refusing to discard them." >&2
  exit 2
fi

show_delta "$CURRENT_SHA" "$TARGET_SHA"
echo

git -C "$OPS" checkout --detach "$TARGET" --quiet
echo "checked out $TARGET"

# A new release may add gitignored runtime paths, and a checkout can leave a
# freshly-tracked file where a symlink belongs.
"$LINK_SCRIPT" >/dev/null
"$LINK_SCRIPT" --check | tail -1

echo
echo "deployed: $(git -C "$OPS" describe --tags --exact-match HEAD 2>/dev/null || git -C "$OPS" rev-parse --short HEAD)"
echo "VERSION : $(cat "$OPS/VERSION" 2>/dev/null || echo '?')"
echo
echo "Roll back with:  $0 $CURRENT_DESC"

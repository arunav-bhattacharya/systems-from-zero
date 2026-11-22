#!/bin/zsh
# Ship only finished files: commit them, build in a clean worktree at that commit, fast-forward main, push,
# upload shipped MP4s to the GitHub release "videos", and deploy the rest to Cloudflare from the worktree.
# Usage (from the repo root): tools/ship.sh "<commit subject>" <file>...
set -e
REPO="$(pwd)"
WT="${TMPDIR:-/tmp}/sfz-shipwt"
PY=/usr/local/bin/python3
MSG="$1"; shift
for f in "$@"; do
  case "$f" in content/lessons/*)
    $PY -c "import json,sys; d=json.load(open('$f')); sys.exit(0 if d.get('opening') and d.get('closing') else 1)" || { echo "NOT REWRITTEN: $f"; exit 1; } ;;
  esac
done
git add -- "$@"
git diff --cached --quiet || git commit -q -m "$MSG

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"
git worktree prune
git worktree add -q --detach "$WT" HEAD
cd "$WT"
if $PY site/validate.py --all 2>&1 | grep -qE '\(([1-9][0-9]*) errors'; then echo "VALIDATION FAILED"; exit 1; fi
OUT=$($PY site/build.py 2>&1 | tail -1); echo "$OUT"
echo "$OUT" | grep -q '158/158 lessons ready' || { echo "BUILD FAILED"; exit 1; }
git add web/index.html web/lessons
git diff --cached --quiet || git commit -q -m "Build the site: $MSG

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
SHA=$(git rev-parse HEAD)
cd "$REPO"
git merge -q --ff-only "$SHA"
GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push -q origin main
cd "$WT"
MP4S=(); for f in "$@"; do case "$f" in web/video/*.mp4) MP4S+=("$f") ;; esac; done
if (( ${#MP4S[@]} )); then gh release upload videos "${MP4S[@]}" --repo arunav-bhattacharya/systems-from-zero --clobber || { echo "RELEASE UPLOAD FAILED"; exit 1; }; echo "uploaded ${#MP4S[@]} video(s) to the release"; fi
BIG=$(find web -type f -size +24M -not -name '*.mp4'); [ -z "$BIG" ] || { echo "OVER 24 MiB (Cloudflare limit is 25): $BIG"; exit 1; }
DEP=$(npx wrangler deploy 2>&1); echo "$DEP" | grep -E 'Uploaded [0-9]+ files|Deployed' | head -3
echo "$DEP" | grep -q 'Deployed' || { echo "DEPLOY FAILED"; echo "$DEP" | tail -12; exit 1; }
cd "$REPO"
git log --oneline -2

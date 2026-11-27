#!/usr/bin/env bash
# Print the Markdown release notes for a tag: every commit since the previous
# tag reachable from it, merged pull requests listed first.
#
#   scripts/release_notes.sh v0.0.37            # notes for an existing tag
#   scripts/release_notes.sh HEAD               # preview before tagging
#
# Used by the release workflow (.github/workflows/docker-publish.yml) to fill
# the GitHub Release body. Needs the full history and tags (fetch-depth: 0).
set -euo pipefail

tag="${1:?usage: release_notes.sh <tag-or-ref>}"
repo_url="${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-datagems-eosc/dataset-profiler}"

# The nearest tag in the tag's own history, not the most recently created one:
# tags are not always created in version order (v0.0.33 came after v0.0.34).
previous="$(git describe --tags --abbrev=0 --match 'v*' "${tag}^" 2>/dev/null || true)"

if [[ -n "$previous" ]]; then
  range="${previous}..${tag}"
  echo "## Changes since ${previous}"
else
  range="${tag}"
  echo "## Changes"
fi
echo

merges="$(git log --merges --format='%s' "$range" | sed -nE 's/^Merge pull request #([0-9]+) from [^/]+\/(.*)$/- #\1 (`\2`)/p')"
if [[ -n "$merges" ]]; then
  echo "### Merged pull requests"
  echo
  echo "$merges"
  echo
fi

echo "### Commits"
echo
commits="$(git log --no-merges --format="- %s ([\`%h\`](${repo_url}/commit/%H)), %an" "$range")"
if [[ -n "$commits" ]]; then
  echo "$commits"
else
  echo "_No commits._"
fi

if [[ -n "$previous" ]]; then
  echo
  echo "**Full diff:** ${repo_url}/compare/${previous}...${tag}"
fi

#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "usage: $0 <current-tag> [output-file]" >&2
  exit 1
fi

CURRENT_TAG="$1"
OUTPUT_FILE="${2:-}"
REPO_URL="${REPO_URL:-https://github.com/vincentkoc/dexscraper}"
PREV_TAG="$(git tag --sort=-version:refname | grep -v "^${CURRENT_TAG}$" | head -n 1 || true)"

if [ -n "$PREV_TAG" ]; then
  RANGE="${PREV_TAG}..${CURRENT_TAG}"
else
  RANGE="${CURRENT_TAG}"
fi

COMMITS="$(git log --pretty=format:'%h%x09%s' "${RANGE}" || true)"

emit() {
  if [ -n "$OUTPUT_FILE" ]; then
    printf '%s\n' "$1" >> "$OUTPUT_FILE"
  else
    printf '%s\n' "$1"
  fi
}

if [ -n "$OUTPUT_FILE" ]; then
  : > "$OUTPUT_FILE"
fi

add_section() {
  local title="$1"
  local pattern="$2"
  local matches
  matches="$(printf '%s\n' "${COMMITS}" | grep -E "${pattern}" || true)"
  [ -n "$matches" ] || return 0
  emit "### ${title}"
  while IFS=$'\t' read -r sha subject; do
    [ -n "$sha" ] || continue
    emit "- ${subject} (\`${sha}\`)"
  done <<< "$matches"
  emit ""
}

emit "## What's Changed"
emit ""

add_section "Features" '^([[:space:]]*)?feat(\([^)]+\))?:'
add_section "Fixes" '^([[:space:]]*)?fix(\([^)]+\))?:'
add_section "Performance" '^([[:space:]]*)?perf(\([^)]+\))?:'
add_section "Refactors" '^([[:space:]]*)?refactor(\([^)]+\))?:'
add_section "Documentation" '^([[:space:]]*)?docs(\([^)]+\))?:'
add_section "Build & CI" '^([[:space:]]*)?(build|ci)(\([^)]+\))?:'
add_section "Tests" '^([[:space:]]*)?test(\([^)]+\))?:'
add_section "Chores" '^([[:space:]]*)?chore(\([^)]+\))?:'

OTHER="$(printf '%s\n' "${COMMITS}" | grep -Ev '^([[:space:]]*)?(feat|fix|perf|refactor|docs|build|ci|test|chore)(\([^)]+\))?:' || true)"
if [ -n "$OTHER" ]; then
  emit "### Other Changes"
  while IFS=$'\t' read -r sha subject; do
    [ -n "$sha" ] || continue
    emit "- ${subject} (\`${sha}\`)"
  done <<< "$OTHER"
  emit ""
fi

if [ -n "$PREV_TAG" ]; then
  emit "Full Changelog: ${REPO_URL}/compare/${PREV_TAG}...${CURRENT_TAG}"
else
  emit "Full Changelog: ${REPO_URL}/tree/${CURRENT_TAG}"
fi

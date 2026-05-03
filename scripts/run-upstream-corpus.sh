#!/usr/bin/env bash
# Top-level driver for the upstream-corpus harness.
#
# Fetches sqlite's upstream test/ if not already present, extracts SQL
# fragments, and runs them through our grammar. Exits non-zero if any
# fragment outside the allowlist fails to parse.
#
# Intended to be the single entry point invoked by:
#   - developers locally
#   - .github/workflows/ci.yml

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

scripts/fetch-test-corpus.sh
scripts/extract-sql-fragments.py vendor/sqlite-test-corpus/test/*.test \
    | scripts/parse-upstream-corpus.py "$@"

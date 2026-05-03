#!/usr/bin/env bash
# Top-level driver for the grammar-coverage harness.
#
# Combines the hand-written corpus under test/corpus/ with the
# upstream sqlite test corpus, parses everything, and reports which
# named node types were exercised. A type that is never hit by ANY
# input across this combined corpus is dead code, unreachable, or
# under-tested.
#
# Exits non-zero if coverage is below the configured threshold.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

scripts/fetch-test-corpus.sh

# Pipe extracted upstream fragments into the coverage tool, which
# also picks up the hand-written corpus on its own.
scripts/extract-sql-fragments.py vendor/sqlite-test-corpus/test/*.test \
    | scripts/grammar-coverage.py "$@"

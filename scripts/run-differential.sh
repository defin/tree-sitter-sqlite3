#!/usr/bin/env bash
# Top-level driver for the differential harness.
#
# Extracts SQL fragments from the upstream sqlite test corpus and pipes
# them through both libsqlite3 (via ctypes) and our grammar, then
# reports the four-way agreement / disagreement counts. Exits non-zero
# if any non-allowlisted SS-AR (sqlite-accepts-we-reject) cases remain
# above the configured threshold.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

scripts/fetch-test-corpus.sh
scripts/extract-sql-fragments.py vendor/sqlite-test-corpus/test/*.test \
    | scripts/differential-test.py "$@"

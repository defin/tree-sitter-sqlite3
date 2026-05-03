#!/usr/bin/env bash
# Top-level driver for the snapshot regression suite.
#
# Default mode is --check: parse each input in test/snapshots/inputs.txt
# and compare against the stored snapshot at test/snapshots/<sha>.sexp.
# Pass --update to regenerate snapshots after intentional grammar
# changes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

scripts/snapshot-test.py "$@"

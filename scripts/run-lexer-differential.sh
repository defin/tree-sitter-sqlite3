#!/usr/bin/env bash
# Top-level driver for the lexer-level differential.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
scripts/lexer-differential-test.py "$@"

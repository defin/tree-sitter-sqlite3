#!/usr/bin/env bash
# Top-level driver for the keyword-fallback coverage matrix.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
scripts/gen-fallback-tests.py "$@"

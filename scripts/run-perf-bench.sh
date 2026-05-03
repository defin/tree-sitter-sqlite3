#!/usr/bin/env bash
# Top-level driver for the performance regression suite.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
scripts/perf-bench.py "$@"

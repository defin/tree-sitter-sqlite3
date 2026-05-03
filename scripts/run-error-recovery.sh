#!/usr/bin/env bash
# Top-level driver for the error-recovery quality suite.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
scripts/error-recovery-test.py "$@"

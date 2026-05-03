#!/usr/bin/env bash
# Top-level driver for the roundtrip property suite.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
scripts/roundtrip-property-test.py "$@"

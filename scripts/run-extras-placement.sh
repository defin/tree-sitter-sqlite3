#!/usr/bin/env bash
# Top-level driver for the extras-placement matrix.
#
# Splices `--` and `/* */` comments between every pair of adjacent
# tokens in the snapshot input set, then asserts every variant
# parses and produces the same tree shape as the no-comment baseline.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

scripts/extras-placement-test.py "$@"

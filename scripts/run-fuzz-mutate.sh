#!/usr/bin/env bash
# Top-level driver for the mutation-based fuzzer.
# Deterministic: fixed seed + iter count -> bit-stable output.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
scripts/fuzz-mutate.py "$@"

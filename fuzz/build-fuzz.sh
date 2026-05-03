#!/usr/bin/env bash
# Build the libFuzzer harness for tree-sitter-sqlite3.
#
# Requires clang with libFuzzer support. The dev container has it
# (Debian's clang ships with libFuzzer in the runtime).
#
# Usage:
#   fuzz/build-fuzz.sh [output-path]   # default: fuzz/fuzz_target

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
out="${1:-$REPO_ROOT/fuzz/fuzz_target}"

# Compile parser.c + scanner.c as C (clang in C mode), then link with
# the C++ fuzz target. Generated parser.c has casts that are valid C
# but rejected when compiled as C++.
SAN_FLAGS="-fsanitize=fuzzer-no-link,address,undefined"
tmp="$(mktemp -d -p "$REPO_ROOT/build" fuzz-build.XXXXXX)"
trap 'rm -rf "$tmp"' EXIT

clang -O1 -g $SAN_FLAGS \
    -I "$REPO_ROOT/src" \
    -c "$REPO_ROOT/src/parser.c" -o "$tmp/parser.o"
clang -O1 -g $SAN_FLAGS \
    -I "$REPO_ROOT/src" \
    -c "$REPO_ROOT/src/scanner.c" -o "$tmp/scanner.o"
clang++ -O1 -g \
    -fsanitize=fuzzer,address,undefined \
    -I "$REPO_ROOT/src" \
    "$REPO_ROOT/fuzz/fuzz_target.cc" \
    "$tmp/parser.o" "$tmp/scanner.o" \
    -ltree-sitter \
    -o "$out"

echo "built $out"

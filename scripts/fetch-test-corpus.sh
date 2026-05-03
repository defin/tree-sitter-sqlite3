#!/usr/bin/env bash
#
# Fetches sqlite's upstream test/ directory at the version pinned in
# vendor/README.md and stages it under vendor/sqlite-test-corpus/.
#
# The corpus itself is NOT committed to this repo (see .gitignore) —
# it is multi-megabyte upstream content reproducibly fetchable from
# the pinned tag. This script is the single source of truth for HOW
# we fetch it.
#
# Usage:
#   scripts/fetch-test-corpus.sh                  # fetch (idempotent)
#   scripts/fetch-test-corpus.sh --force          # re-fetch even if present
#   scripts/fetch-test-corpus.sh --tag <tagname>  # override pinned tag
#
# Exits non-zero on network failure or sha mismatch.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO_ROOT/vendor/sqlite-test-corpus"

# The pinned upstream sqlite version. Keep in sync with vendor/README.md.
DEFAULT_TAG="version-3.47.0"
TAG="$DEFAULT_TAG"
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=1; shift ;;
        --tag)   TAG="$2"; shift 2 ;;
        -h|--help)
            sed -n 's/^# \{0,1\}//p' "$0" | sed -n '/^Fetches/,/^Exits/p'
            exit 0
            ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ -d "$DEST/test" && $FORCE -eq 0 ]]; then
    echo "vendor/sqlite-test-corpus/test/ already present (use --force to re-fetch)"
    exit 0
fi

# Stage the tarball under build/ so we don't pollute /tmp and so the
# download is reusable across runs. build/ is gitignored.
mkdir -p "$REPO_ROOT/build"
TMPDIR="$(mktemp -d -p "$REPO_ROOT/build" fetch-corpus.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

# sqlite tarballs by tag from the canonical mirror at github.com/sqlite/sqlite.
# The sqlite-foundation hosts at sqlite.org but doesn't expose tarballs at
# arbitrary tags via plain https; github does.
URL="https://github.com/sqlite/sqlite/archive/refs/tags/${TAG}.tar.gz"

echo "Fetching $URL ..."
curl -fsSL "$URL" -o "$TMPDIR/sqlite.tar.gz"

echo "Extracting test/ ..."
mkdir -p "$DEST"
# --wildcards on GNU tar; --strip-components peels the top-level
# sqlite-version-N.N.N/ directory.
tar -xzf "$TMPDIR/sqlite.tar.gz" \
    -C "$DEST" \
    --strip-components=1 \
    --wildcards "*/test/*"

# Sanity: did we get something?
if [[ ! -d "$DEST/test" ]] || [[ -z "$(ls -A "$DEST/test" 2>/dev/null)" ]]; then
    echo "fetch failed: $DEST/test is empty after extraction" >&2
    exit 1
fi

count="$(find "$DEST/test" -name '*.test' -type f | wc -l)"
echo "Fetched ${count} .test files into $DEST/test/"
echo "Tag: $TAG"

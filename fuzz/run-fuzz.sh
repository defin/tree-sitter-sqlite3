#!/usr/bin/env bash
# Top-level driver for the libFuzzer harness.
#
# In CI: budgeted to 60 seconds per push. Crashes are written to
# fuzz/findings/ — committing a crashing input makes it a regression
# test (the harness re-runs that exact input on every CI build).
#
# Local long-runs: pass --max-total-time on the command line.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Build if needed.
if [ ! -x fuzz/fuzz_target ] || [ src/parser.c -nt fuzz/fuzz_target ]; then
    fuzz/build-fuzz.sh
fi

# Seed the corpus from snapshot inputs if corpus is empty.
mkdir -p fuzz/corpus fuzz/findings
if [ -z "$(ls -A fuzz/corpus 2>/dev/null)" ]; then
    echo "seeding corpus from test/snapshots/inputs.txt"
    python3 -c '
import hashlib, pathlib
inputs = pathlib.Path("test/snapshots/inputs.txt").read_text().splitlines()
out = pathlib.Path("fuzz/corpus")
out.mkdir(exist_ok=True)
for raw in inputs:
    if not raw or raw.startswith("#"):
        continue
    sql = raw.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
    name = hashlib.sha256(sql.encode()).hexdigest()[:16]
    (out / f"seed-{name}").write_text(sql)
print(f"seeded {len(list(out.iterdir()))} files")
'
fi

# Default budget: 60 seconds (CI). Override with --max-total-time.
default_args=(
    fuzz/corpus
    fuzz/findings
    -max_total_time=60
    -timeout=10
    -rss_limit_mb=512
    -print_final_stats=1
)
exec fuzz/fuzz_target "${default_args[@]}" "$@"

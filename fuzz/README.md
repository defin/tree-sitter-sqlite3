# fuzz/

libFuzzer + ASAN/UBSAN harness on the parser `.so`. Targets the
generated parser (`src/parser.c`) and external scanner
(`src/scanner.c`) — the latter does manual byte-walking and is the
highest-risk component.

## Build

Requires `clang` with libFuzzer (Debian's `clang` package ships
it). Inside the dev container or any clang environment:

```sh
fuzz/build-fuzz.sh                  # → fuzz/fuzz_target
```

Compiles `parser.c` + `scanner.c` as C, links with the C++ harness
(`fuzz_target.cc`) and `-ltree-sitter`.

## Run

```sh
fuzz/run-fuzz.sh                    # 60s budget, default in CI
fuzz/run-fuzz.sh -max_total_time=600
```

The runner builds if needed, seeds the corpus from
`test/snapshots/inputs.txt` if `fuzz/corpus/` is empty, and invokes
the harness with libFuzzer-standard flags.

## Findings

Crashes / hangs / OOM hits land in `fuzz/findings/`. Committing a
finding makes it a regression test — `fuzz/run-fuzz.sh` re-runs
the entire `fuzz/corpus/` and `fuzz/findings/` set on every CI
build before extending into new territory.

## CI

`fuzz-libfuzzer` job in `.github/workflows/ci.yml`. Budget: 60 s
per push. Longer nightly cron runs are reasonable to add when
findings stabilise.

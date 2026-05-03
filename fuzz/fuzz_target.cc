// libFuzzer harness for tree-sitter-sqlite3.
//
// Calls ts_parser_parse_string on libFuzzer-provided input. Goal:
// find inputs that segfault, hang, OOM, or trigger any other
// undefined behaviour in the generated parser + external scanner.
//
// Build (in dev container):
//   clang++ -O1 -g -fsanitize=fuzzer,address,undefined \
//           -I src \
//           src/parser.c src/scanner.c fuzz/fuzz_target.cc \
//           -o fuzz/fuzz_target -lc
//
// Run:
//   fuzz/fuzz_target -max_total_time=600 fuzz/corpus
//
// Corpus is seeded from test/snapshots/inputs.txt by the runner
// script. Findings (crashes/hangs) get committed to fuzz/corpus/
// or fuzz/findings/ for regression tracking.
//
// Note: tree-sitter's parser is the load-bearing thing here, but our
// custom external scanner (src/scanner.c) is the highest-risk
// component — it does manual byte walking and could be coaxed into
// reading past the input bounds with the right input shape.

#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>

#include "tree_sitter/parser.h"

extern "C" {
    const TSLanguage *tree_sitter_sqlite3(void);

    // Tree-sitter C API surface.
    typedef struct TSParser TSParser;
    typedef struct TSTree TSTree;
    typedef struct TSNode {
        uint32_t context[4];
        const void *id;
        const TSTree *tree;
    } TSNode;

    TSParser *ts_parser_new(void);
    void ts_parser_delete(TSParser *p);
    bool ts_parser_set_language(TSParser *p, const TSLanguage *lang);
    void ts_parser_set_timeout_micros(TSParser *p, uint64_t t);
    TSTree *ts_parser_parse_string(TSParser *p, const TSTree *old,
                                   const char *input, uint32_t length);
    void ts_tree_delete(TSTree *tree);
    TSNode ts_tree_root_node(const TSTree *tree);
    bool ts_node_has_error(TSNode);
}

extern "C" int LLVMFuzzerInitialize(int *argc, char ***argv) {
    (void)argc;
    (void)argv;
    return 0;
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size == 0 || size > 1 << 20) {
        // Skip huge inputs — they only stress the regex engine, not
        // grammar logic.
        return 0;
    }
    TSParser *p = ts_parser_new();
    ts_parser_set_language(p, tree_sitter_sqlite3());
    // Bound parse time so the fuzzer doesn't latch on a pathological
    // input that takes minutes per iteration.
    ts_parser_set_timeout_micros(p, 500000);  // 500 ms

    TSTree *tree = ts_parser_parse_string(
        p, nullptr,
        reinterpret_cast<const char *>(data),
        static_cast<uint32_t>(size)
    );
    if (tree) {
        // Touch the root node so the parser must have produced a
        // structurally valid tree (ts_tree_root_node returns a node
        // even for ERROR-recovered trees; just make sure we can
        // read it without crashing).
        TSNode root = ts_tree_root_node(tree);
        (void)ts_node_has_error(root);
        ts_tree_delete(tree);
    }
    ts_parser_delete(p);
    return 0;
}

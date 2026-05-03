/*
 * sqlite-tokenize: a small shim that reads SQL from stdin and prints
 * one `<offset>\t<length>\t<token-code>` line per token, using
 * sqlite's own tokenize.c (sqlite3GetToken).
 *
 * Built against the sqlite amalgamation with -DSQLITE_PRIVATE= so
 * the otherwise-static sqlite3GetToken / sqlite3KeywordCode symbols
 * are exported.
 *
 * Used by scripts/lexer-differential-test.py to compare
 * sqlite's token sequence against tree-sitter's leaf walk on the
 * same input.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "sqlite3.h"

/* sqlite3GetToken's signature in tokenize.c:
 *   int sqlite3GetToken(const unsigned char *z, int *tokenType);
 * Returns the byte length of the token; *tokenType receives the
 * TK_* code. The amalgamation marks it static; we build the
 * amalgamation with -DSQLITE_PRIVATE= to expose it. */
extern int sqlite3GetToken(const unsigned char *z, int *tokenType);

static char *read_all_stdin(size_t *out_len) {
    size_t cap = 4096, n = 0;
    char *buf = malloc(cap);
    if (!buf) return NULL;
    for (;;) {
        if (n + 1 >= cap) {
            cap *= 2;
            char *nb = realloc(buf, cap);
            if (!nb) { free(buf); return NULL; }
            buf = nb;
        }
        ssize_t r = read(0, buf + n, cap - n - 1);
        if (r < 0) { free(buf); return NULL; }
        if (r == 0) break;
        n += (size_t)r;
    }
    buf[n] = '\0';
    *out_len = n;
    return buf;
}

int main(void) {
    size_t len = 0;
    char *sql = read_all_stdin(&len);
    if (!sql) {
        fprintf(stderr, "sqlite-tokenize: failed to read stdin\n");
        return 2;
    }

    const unsigned char *z = (const unsigned char *)sql;
    size_t off = 0;
    while (off < len) {
        int tt = 0;
        int n = sqlite3GetToken(z + off, &tt);
        if (n <= 0) {
            /* Defensive: sqlite returns 0 on tokens it can't recognize
             * (would normally cause prepare to error). Advance by one
             * byte and continue so we still emit something for the
             * remaining bytes; the caller can decide how to interpret. */
            n = 1;
        }
        printf("%zu\t%d\t%d\n", off, n, tt);
        off += (size_t)n;
    }
    free(sql);
    return 0;
}

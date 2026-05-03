# tree-sitter-sqlite3 — C binding

Header + pkg-config integration. Build the static / shared library
and install via `make`:

```sh
make
sudo make install               # honours PREFIX, DESTDIR, etc.
```

Then in your build:

```c
#include <tree_sitter/tree-sitter-sqlite3.h>

const TSLanguage *tree_sitter_sqlite3(void);
```

`pkg-config --cflags --libs tree-sitter-sqlite3` resolves the include
path and links `-ltree-sitter-sqlite3`.

See the repository [README](https://github.com/defin/tree-sitter-sqlite3) for full project documentation.

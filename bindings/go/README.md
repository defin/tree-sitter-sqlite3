# tree-sitter-sqlite3 — Go binding

Tree-sitter grammar for SQLite's SQL dialect plus dot-commands.

```go
package main

import (
    sitter "github.com/tree-sitter/go-tree-sitter"
    sqlite3 "github.com/defin/tree-sitter-sqlite3/bindings/go"
)

func main() {
    parser := sitter.NewParser()
    defer parser.Close()
    parser.SetLanguage(sitter.NewLanguage(sqlite3.Language()))
    tree := parser.Parse([]byte("SELECT 1;"), nil)
    defer tree.Close()
}
```

See the repository [README](https://github.com/defin/tree-sitter-sqlite3) for full project documentation, source-of-truth process, and contribution model.

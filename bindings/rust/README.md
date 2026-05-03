# tree-sitter-sqlite3 — Rust binding

Tree-sitter grammar for SQLite's SQL dialect plus dot-commands.

```rust
let code = "SELECT 1;";
let mut parser = tree_sitter::Parser::new();
parser.set_language(&tree_sitter_sqlite3::LANGUAGE.into())?;
let tree = parser.parse(code, None).unwrap();
```

See the repository [README](https://github.com/defin/tree-sitter-sqlite3) for full project documentation, source-of-truth process, and contribution model.

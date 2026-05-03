# tree-sitter-sqlite3 — Python binding

Tree-sitter grammar for SQLite's SQL dialect plus dot-commands.

```python
import tree_sitter, tree_sitter_sqlite3

lang = tree_sitter.Language(tree_sitter_sqlite3.language())
parser = tree_sitter.Parser(lang)
tree = parser.parse(b"SELECT 1;")
```

See the repository [README](https://github.com/defin/tree-sitter-sqlite3) for full project documentation, source-of-truth process, and contribution model.

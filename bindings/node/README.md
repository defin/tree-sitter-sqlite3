# tree-sitter-sqlite3 — Node binding

Tree-sitter grammar for SQLite's SQL dialect plus dot-commands.

```js
const Parser = require("tree-sitter");
const Sqlite3 = require("tree-sitter-sqlite3");

const parser = new Parser();
parser.setLanguage(Sqlite3);
const tree = parser.parse("SELECT 1;");
```

See the repository [README](https://github.com/defin/tree-sitter-sqlite3) for full project documentation, source-of-truth process, and contribution model.

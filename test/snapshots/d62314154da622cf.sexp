# input:
#   REINDEX users;
---
(source_file
  (reindex_statement
    target: (qualified_table_name
      name: (identifier))))

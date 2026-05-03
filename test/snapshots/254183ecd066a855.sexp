# input:
#   ATTACH 'mydb.sqlite' AS mydb;
---
(source_file
  (attach_statement
    source: (string_literal)
    schema: (column_reference
      name: (identifier))))

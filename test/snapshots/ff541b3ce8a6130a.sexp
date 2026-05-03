# input:
#   ATTACH DATABASE 'enc.db' AS enc KEY 'secret';
---
(source_file
  (attach_statement
    source: (string_literal)
    schema: (column_reference
      name: (identifier))
    key: (string_literal)))

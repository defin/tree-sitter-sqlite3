# input:
#   DETACH DATABASE mydb;
---
(source_file
  (detach_statement
    schema: (column_reference
      name: (identifier))))

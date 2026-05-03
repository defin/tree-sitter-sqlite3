# input:
#   DELETE FROM users NOT INDEXED WHERE id = 1;
---
(source_file
  (delete_statement
    target: (qualified_table_name
      name: (identifier))
    where: (where_clause
      (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))))

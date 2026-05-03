# input:
#   INSERT INTO t VALUES (1 + 2 * 3);
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    source: (values_clause
      value: (binary_expression
        left: (numeric_literal)
        right: (binary_expression
          left: (numeric_literal)
          right: (numeric_literal))))))

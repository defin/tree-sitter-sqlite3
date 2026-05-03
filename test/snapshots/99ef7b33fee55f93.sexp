# input:
#   DELETE FROM t WHERE id = 1 RETURNING id;
---
(source_file
  (delete_statement
    target: (qualified_table_name
      name: (identifier))
    where: (where_clause
      (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))
    returning: (returning_clause
      (result_column_list
        (expression_result_column
          expression: (column_reference
            name: (identifier)))))))

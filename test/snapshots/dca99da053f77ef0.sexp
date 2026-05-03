# input:
#   SELECT id FROM users WHERE id = 1;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (column_reference
          name: (identifier))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))
    where: (where_clause
      (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))))

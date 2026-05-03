# input:
#   SELECT id FROM users GROUP BY id HAVING id > 1;
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
    group_by: (group_by_clause
      expression: (column_reference
        name: (identifier)))
    having: (having_clause
      having: (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))))

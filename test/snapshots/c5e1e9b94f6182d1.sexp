# input:
#   SELECT name FROM users ORDER BY id DESC LIMIT 10;
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
    order_by: (order_by_clause
      (order_term
        (column_reference
          name: (identifier))))
    limit: (limit_clause
      (numeric_literal))))

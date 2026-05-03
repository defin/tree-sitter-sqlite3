# input:
#   SELECT rank() OVER w FROM t WINDOW w AS (ORDER BY id);
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (function_call
          name: (identifier)
          over: (over_clause
            window_name: (identifier)))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))
    window: (window_clause
      (named_window
        name: (identifier)
        (window_definition
          (order_by_clause
            (order_term
              (column_reference
                name: (identifier)))))))))

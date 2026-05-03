# input:
#   SELECT sum(x) OVER (ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM t;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (function_call
          name: (identifier)
          arguments: (normal_function_arguments
            (column_reference
              name: (identifier)))
          over: (over_clause
            (window_definition
              (order_by_clause
                (order_term
                  (column_reference
                    name: (identifier))))
              (window_frame_clause
                start: (window_frame_bound)
                end: (window_frame_bound)))))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
